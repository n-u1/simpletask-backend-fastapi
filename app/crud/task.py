"""タスクCRUDクラス

タスクのデータアクセス層を提供
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import APIConstants, TaskStatus
from app.crud.base import CRUDBase
from app.models.tag import Tag
from app.models.task import Task
from app.models.task_tag import TaskTag
from app.schemas.task import TaskCreate, TaskFilters, TaskSortOptions, TaskUpdate
from app.utils.db_helpers import (
    QueryBuilder,
    create_count_query,
    create_user_resource_query,
    safe_uuid_convert,
)
from app.utils.error_handler import handle_db_operation


class CRUDTask(CRUDBase[Task, TaskCreate, TaskUpdate]):
    @handle_db_operation("ユーザータスク取得")
    async def get_by_user(self, db: AsyncSession, user_id: UUID, task_id: UUID) -> Task | None:
        """ユーザーIDとタスクIDでタスクを取得"""
        safe_user_id = safe_uuid_convert(user_id, "ユーザーID")
        safe_task_id = safe_uuid_convert(task_id, "タスクID")

        query = create_user_resource_query(Task, safe_user_id, target_id=safe_task_id, with_relations=True)

        result: Any = await db.execute(query)
        task_result: Task | None = result.scalar_one_or_none()
        return task_result

    @handle_db_operation("ユーザータスク一覧取得")
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
        # UUIDの安全な変換
        safe_user_id = safe_uuid_convert(user_id, "ユーザーID")

        # QueryBuilderを使用したクエリ構築
        builder = QueryBuilder(Task)
        builder.with_task_tags().filter_by_user(safe_user_id)

        # フィルタリング適用
        if filters:
            builder.query = self._apply_filters(builder.query, filters)

        # ソート適用
        if sort_options:
            builder.query = self._apply_sort(builder.query, sort_options)
        else:
            builder.order_by_default()

        # ページネーション
        builder.paginate(skip, limit)

        # クエリ実行
        result: Any = await db.execute(builder.build())
        tasks_result: list[Task] = list(result.scalars().all())
        return tasks_result

    @handle_db_operation("ユーザータスク数取得")
    async def count_by_user(self, db: AsyncSession, user_id: UUID, filters: TaskFilters | None = None) -> int:
        """ユーザーのタスク総数を取得"""
        # UUIDの安全な変換
        safe_user_id = safe_uuid_convert(user_id, "ユーザーID")

        # カウントクエリ
        query = create_count_query(Task, safe_user_id)

        # フィルタリング適用
        if filters:
            query = self._apply_filters(query, filters)

        result: Any = await db.execute(query)
        count_result: int = result.scalar() or 0
        return count_result

    @handle_db_operation("タグ付きタスク作成")
    async def create_with_tags(self, db: AsyncSession, *, task_in: TaskCreate, user_id: UUID) -> Task:
        """タスクをタグと一緒に作成"""
        # UUIDの安全な変換
        safe_user_id = safe_uuid_convert(user_id, "ユーザーID")

        # タスク作成データの準備
        task_data = task_in.model_dump(exclude={"tag_ids"})
        task_data["user_id"] = safe_user_id

        # タスク作成
        db_task = self.model(**task_data)
        db.add(db_task)
        await db.flush()  # IDを取得するため

        # タグとの関連付け
        if task_in.tag_ids:
            await self._create_task_tag_associations(db, db_task.id, task_in.tag_ids, safe_user_id)

        await db.commit()
        await db.refresh(db_task)

        # タグ情報を含めて取得
        task_with_tags = await self.get_by_user(db, safe_user_id, db_task.id)
        return task_with_tags or db_task

    @handle_db_operation("タグ付きタスク更新")
    async def update_with_tags(self, db: AsyncSession, *, db_task: Task, task_in: TaskUpdate) -> Task:
        """タスクをタグと一緒に更新"""
        # タスク更新データの準備
        update_data = task_in.model_dump(exclude_unset=True, exclude={"tag_ids"})

        # ステータス変更時の自動処理
        if "status" in update_data:
            if update_data["status"] == TaskStatus.DONE.value and not db_task.completed_at:
                # Taskモデルのメソッドを使用
                db_task.mark_completed()
                update_data.pop("status", None)  # statusはmark_completed()で設定されるため削除
            elif update_data["status"] != TaskStatus.DONE.value and db_task.completed_at:
                # Taskモデルのメソッドを使用
                db_task.mark_uncompleted()
                if update_data["status"] != TaskStatus.TODO.value:
                    db_task.status = update_data[
                        "status"
                    ]  # mark_uncompleted()はTODOにするため、別のステータスの場合は再設定
                update_data.pop("status", None)  # statusは手動で設定したため削除

        # タスク更新
        for field, value in update_data.items():
            setattr(db_task, field, value)

        # タグの更新
        if task_in.tag_ids is not None:
            await self._update_task_tag_associations(db, db_task.id, task_in.tag_ids, db_task.user_id)

        await db.commit()
        await db.refresh(db_task)

        # タグ情報を含めて取得
        task_with_tags = await self.get_by_user(db, db_task.user_id, db_task.id)
        return task_with_tags or db_task

    @handle_db_operation("タスクステータス更新")
    async def update_status(self, db: AsyncSession, *, db_task: Task, status: TaskStatus) -> Task:
        """タスクのステータスのみ更新"""
        # Taskモデルのメソッドを使用
        if status == TaskStatus.DONE:
            db_task.mark_completed()
        elif db_task.status == TaskStatus.DONE.value and status.value != TaskStatus.DONE.value:
            db_task.mark_uncompleted()
            if status.value != TaskStatus.TODO.value:
                db_task.status = status.value  # mark_uncompleted()はTODOにするため、別のステータスの場合は再設定
        else:
            db_task.status = status.value

        await db.commit()
        await db.refresh(db_task)
        return db_task

    @handle_db_operation("タスク位置更新")
    async def update_positions(
        self, db: AsyncSession, *, position_updates: list[dict[str, Any]], user_id: UUID
    ) -> bool:
        """複数タスクの位置を一括更新（ドラッグ&ドロップ用）"""
        # UUIDの安全な変換
        safe_user_id = safe_uuid_convert(user_id, "ユーザーID")

        for update_data in position_updates:
            task_id = safe_uuid_convert(update_data["id"], "タスクID")
            new_position = update_data["position"]
            new_status = update_data.get("status")

            # 更新クエリの構築
            update_values = {"position": new_position}
            if new_status:
                update_values["status"] = new_status

            stmt = (
                update(self.model)
                .where(and_(self.model.id == task_id, self.model.user_id == safe_user_id))
                .values(**update_values)
            )
            await db.execute(stmt)

        await db.commit()
        return True

    @handle_db_operation("ステータス別タスク取得")
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
        safe_user_id = safe_uuid_convert(user_id, "ユーザーID")

        builder = QueryBuilder(Task)
        builder.with_task_tags().filter_by_user(safe_user_id)
        builder.where(self.model.status == status.value)
        builder.order_by(self.model.position.asc(), self.model.created_at.desc())
        builder.paginate(skip, limit)

        result: Any = await db.execute(builder.build())
        tasks_result: list[Task] = list(result.scalars().all())
        return tasks_result

    @handle_db_operation("期限切れタスク取得")
    async def get_overdue_tasks(
        self, db: AsyncSession, user_id: UUID, *, skip: int = 0, limit: int = APIConstants.DEFAULT_PAGE_SIZE
    ) -> list[Task]:
        """期限切れタスクを取得"""
        safe_user_id = safe_uuid_convert(user_id, "ユーザーID")

        now = datetime.now(UTC)

        builder = QueryBuilder(Task)
        builder.with_task_tags().filter_by_user(safe_user_id)
        builder.where(
            and_(
                self.model.due_date < now,
                self.model.status != TaskStatus.DONE.value,
                self.model.status != TaskStatus.ARCHIVED.value,
            )
        )
        builder.order_by(self.model.due_date.asc())
        builder.paginate(skip, limit)

        result: Any = await db.execute(builder.build())
        tasks_result: list[Task] = list(result.scalars().all())
        return tasks_result

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
                safe_tag_ids = [safe_uuid_convert(tag_id, "タグID") for tag_id in filters.tag_ids]
                stmt = stmt.where(TaskTag.tag_id.in_(safe_tag_ids))

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

    @handle_db_operation("タスクタグ関連付け作成")
    async def _create_task_tag_associations(
        self, db: AsyncSession, task_id: UUID, tag_ids: list[UUID], user_id: UUID
    ) -> None:
        """タスクとタグの関連付けを作成"""
        safe_task_id = safe_uuid_convert(task_id, "タスクID")
        safe_user_id = safe_uuid_convert(user_id, "ユーザーID")
        safe_tag_ids = [safe_uuid_convert(tag_id, "タグID") for tag_id in tag_ids]

        # タグの存在確認
        stmt = select(Tag.id).where(
            and_(
                Tag.id.in_(safe_tag_ids),
                Tag.user_id == safe_user_id,
                Tag.is_active == True,  # noqa: E712
            )
        )
        result: Any = await db.execute(stmt)
        valid_tag_ids = {row[0] for row in result.fetchall()}

        # 有効なタグのみ関連付け
        for tag_id in safe_tag_ids:
            if tag_id in valid_tag_ids:
                task_tag = TaskTag(task_id=safe_task_id, tag_id=tag_id)
                db.add(task_tag)

    @handle_db_operation("タスクタグ関連付け更新")
    async def _update_task_tag_associations(
        self, db: AsyncSession, task_id: UUID, tag_ids: list[UUID], user_id: UUID
    ) -> None:
        """タスクとタグの関連付けを更新"""
        safe_task_id = safe_uuid_convert(task_id, "タスクID")
        safe_user_id = safe_uuid_convert(user_id, "ユーザーID")

        # 既存の関連付けを削除
        delete_stmt = delete(TaskTag).where(TaskTag.task_id == safe_task_id)
        await db.execute(delete_stmt)

        # 新しい関連付けを作成
        if tag_ids:
            await self._create_task_tag_associations(db, safe_task_id, tag_ids, safe_user_id)


task_crud = CRUDTask(Task)
