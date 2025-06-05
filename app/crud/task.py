"""タスクCRUDクラス

タスクのデータアクセス層を提供
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import APIConstants, TaskStatus
from app.crud.base import CRUDBase
from app.models.tag import Tag
from app.models.task import Task
from app.models.task_tag import TaskTag
from app.schemas.task import TaskCreate, TaskFilters, TaskSortOptions, TaskUpdate


class CRUDTask(CRUDBase[Task, TaskCreate, TaskUpdate]):
    async def get_by_user(self, db: AsyncSession, user_id: UUID, task_id: UUID) -> Task | None:
        """ユーザーIDとタスクIDでタスクを取得"""
        try:
            stmt = (
                select(self.model)
                .options(selectinload(self.model.task_tags).selectinload(TaskTag.tag))
                .where(and_(self.model.id == task_id, self.model.user_id == user_id))
            )
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"ユーザータスク取得エラー: {e}")
            return None

    async def get_multi_by_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        *,
        skip: int = 0,
        limit: int = APIConstants.DEFAULT_PAGE_SIZE,
        filters: TaskFilters | None = None,
        sort_options: TaskSortOptions | None = None,
    ) -> list[Task]:
        """ユーザーのタスク一覧を取得"""
        try:
            # ベースクエリ
            stmt = (
                select(self.model)
                .options(selectinload(self.model.task_tags).selectinload(TaskTag.tag))
                .where(self.model.user_id == user_id)
            )

            # フィルタリング適用
            if filters:
                stmt = self._apply_filters(stmt, filters)

            # ソート適用
            stmt = self._apply_sort(stmt, sort_options) if sort_options else stmt.order_by(self.model.created_at.desc())

            # ページネーション
            stmt = stmt.offset(skip).limit(limit)

            result = await db.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"ユーザータスク一覧取得エラー: {e}")
            return []

    async def count_by_user(self, db: AsyncSession, user_id: UUID, filters: TaskFilters | None = None) -> int:
        """ユーザーのタスク総数を取得"""
        try:
            stmt = select(func.count(self.model.id)).where(self.model.user_id == user_id)

            # フィルタリング適用
            if filters:
                stmt = self._apply_filters(stmt, filters)

            result = await db.execute(stmt)
            return result.scalar() or 0

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"ユーザータスク数取得エラー: {e}")
            return 0

    async def create_with_tags(self, db: AsyncSession, *, task_in: TaskCreate, user_id: UUID) -> Task:
        """タスクをタグと一緒に作成"""
        try:
            # タスク作成データの準備
            task_data = task_in.model_dump(exclude={"tag_ids"})
            task_data["user_id"] = user_id

            # タスク作成
            db_task = self.model(**task_data)
            db.add(db_task)
            await db.flush()  # IDを取得するため

            # タグとの関連付け
            if task_in.tag_ids:
                await self._create_task_tag_associations(db, db_task.id, task_in.tag_ids, user_id)

            await db.commit()
            await db.refresh(db_task)

            # タグ情報を含めて取得
            return await self.get_by_user(db, user_id, db_task.id) or db_task

        except Exception as e:
            await db.rollback()
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"タグ付きタスク作成エラー: {e}")
            raise

    async def update_with_tags(self, db: AsyncSession, *, db_task: Task, task_in: TaskUpdate) -> Task:
        """タスクをタグと一緒に更新"""
        try:
            # タスク更新データの準備
            update_data = task_in.model_dump(exclude_unset=True, exclude={"tag_ids"})

            # ステータス変更時の自動処理
            if "status" in update_data:
                if update_data["status"] == TaskStatus.DONE.value and not db_task.completed_at:
                    update_data["completed_at"] = datetime.now(UTC)
                elif update_data["status"] != TaskStatus.DONE.value and db_task.completed_at:
                    update_data["completed_at"] = None

            # タスク更新
            for field, value in update_data.items():
                setattr(db_task, field, value)

            # タグの更新
            if task_in.tag_ids is not None:
                await self._update_task_tag_associations(db, db_task.id, task_in.tag_ids, db_task.user_id)

            await db.commit()
            await db.refresh(db_task)

            # タグ情報を含めて取得
            return await self.get_by_user(db, db_task.user_id, db_task.id) or db_task

        except Exception as e:
            await db.rollback()
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"タグ付きタスク更新エラー: {e}")
            raise

    async def update_status(self, db: AsyncSession, *, db_task: Task, status: TaskStatus) -> Task:
        """タスクのステータスのみ更新"""
        try:
            db_task.status = status.value

            # 完了時の自動処理
            if status == TaskStatus.DONE and not db_task.completed_at:
                db_task.completed_at = datetime.now(UTC)
            elif status != TaskStatus.DONE and db_task.completed_at:
                db_task.completed_at = None

            await db.commit()
            await db.refresh(db_task)
            return db_task

        except Exception as e:
            await db.rollback()
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"タスクステータス更新エラー: {e}")
            raise

    async def update_positions(
        self, db: AsyncSession, *, position_updates: list[dict[str, Any]], user_id: UUID
    ) -> bool:
        """複数タスクの位置を一括更新（ドラッグ&ドロップ用）"""
        try:
            for update_data in position_updates:
                task_id = update_data["id"]
                new_position = update_data["position"]
                new_status = update_data.get("status")

                # 更新クエリの構築
                update_values = {"position": new_position}
                if new_status:
                    update_values["status"] = new_status

                stmt = (
                    update(self.model)
                    .where(and_(self.model.id == task_id, self.model.user_id == user_id))
                    .values(**update_values)
                )
                await db.execute(stmt)

            await db.commit()
            return True

        except Exception as e:
            await db.rollback()
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"タスク位置更新エラー: {e}")
            return False

    async def get_by_status(
        self,
        db: AsyncSession,
        user_id: UUID,
        status: TaskStatus,
        *,
        skip: int = 0,
        limit: int = APIConstants.DEFAULT_PAGE_SIZE,
    ) -> list[Task]:
        """ステータス別でタスクを取得"""
        try:
            stmt = (
                select(self.model)
                .options(selectinload(self.model.task_tags).selectinload(TaskTag.tag))
                .where(and_(self.model.user_id == user_id, self.model.status == status.value))
                .order_by(self.model.position.asc(), self.model.created_at.desc())
                .offset(skip)
                .limit(limit)
            )

            result = await db.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"ステータス別タスク取得エラー: {e}")
            return []

    async def get_overdue_tasks(
        self, db: AsyncSession, user_id: UUID, *, skip: int = 0, limit: int = APIConstants.DEFAULT_PAGE_SIZE
    ) -> list[Task]:
        """期限切れタスクを取得"""
        try:
            now = datetime.now(UTC)
            stmt = (
                select(self.model)
                .options(selectinload(self.model.task_tags).selectinload(TaskTag.tag))
                .where(
                    and_(
                        self.model.user_id == user_id,
                        self.model.due_date < now,
                        self.model.status != TaskStatus.DONE.value,
                        self.model.status != TaskStatus.ARCHIVED.value,
                    )
                )
                .order_by(self.model.due_date.asc())
                .offset(skip)
                .limit(limit)
            )

            result = await db.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"期限切れタスク取得エラー: {e}")
            return []

    def _apply_filters(self, stmt: Any, filters: TaskFilters) -> Any:
        """フィルタリング条件を適用"""
        if filters.status:
            status_values = [s.value for s in filters.status]
            stmt = stmt.where(self.model.status.in_(status_values))

        if filters.priority:
            priority_values = [p.value for p in filters.priority]
            stmt = stmt.where(self.model.priority.in_(priority_values))

        if filters.due_date_from:
            stmt = stmt.where(self.model.due_date >= filters.due_date_from)
        if filters.due_date_to:
            stmt = stmt.where(self.model.due_date <= filters.due_date_to)

        if filters.is_overdue is not None:
            now = datetime.now(UTC)
            if filters.is_overdue:
                stmt = stmt.where(and_(self.model.due_date < now, self.model.status != TaskStatus.DONE.value))
            else:
                stmt = stmt.where(
                    or_(
                        self.model.due_date >= now,
                        self.model.due_date.is_(None),
                        self.model.status == TaskStatus.DONE.value,
                    )
                )

        if filters.tag_ids or filters.tag_names:
            stmt = stmt.join(TaskTag, self.model.id == TaskTag.task_id)

            if filters.tag_ids:
                stmt = stmt.where(TaskTag.tag_id.in_(filters.tag_ids))

            if filters.tag_names:
                stmt = stmt.join(Tag, TaskTag.tag_id == Tag.id)
                stmt = stmt.where(Tag.name.in_(filters.tag_names))

        if filters.search:
            search_term = f"%{filters.search}%"
            stmt = stmt.where(or_(self.model.title.ilike(search_term), self.model.description.ilike(search_term)))

        return stmt

    def _apply_sort(self, stmt: Any, sort_options: TaskSortOptions) -> Any:
        """ソート条件を適用"""
        sort_field = getattr(self.model, sort_options.sort_by, None)
        if sort_field is None:
            # フィールドが存在しない場合はデフォルトソート
            return stmt.order_by(self.model.created_at.desc())

        if sort_options.order == "desc":
            return stmt.order_by(sort_field.desc())
        else:
            return stmt.order_by(sort_field.asc())

    async def _create_task_tag_associations(
        self, db: AsyncSession, task_id: UUID, tag_ids: list[UUID], user_id: UUID
    ) -> None:
        """タスクとタグの関連付けを作成"""
        # タグの存在確認
        stmt = select(Tag.id).where(
            and_(
                Tag.id.in_(tag_ids),
                Tag.user_id == user_id,
                Tag.is_active == True,  # noqa: E712
            )
        )
        result = await db.execute(stmt)
        valid_tag_ids = {row[0] for row in result.fetchall()}

        # 有効なタグのみ関連付け
        for tag_id in tag_ids:
            if tag_id in valid_tag_ids:
                task_tag = TaskTag(task_id=task_id, tag_id=tag_id)
                db.add(task_tag)

    async def _update_task_tag_associations(
        self, db: AsyncSession, task_id: UUID, tag_ids: list[UUID], user_id: UUID
    ) -> None:
        """タスクとタグの関連付けを更新"""
        # 既存の関連付けを削除
        from sqlalchemy import delete

        delete_stmt = delete(TaskTag).where(TaskTag.task_id == task_id)
        await db.execute(delete_stmt)

        # 新しい関連付けを作成
        if tag_ids:
            await self._create_task_tag_associations(db, task_id, tag_ids, user_id)


task_crud = CRUDTask(Task)
