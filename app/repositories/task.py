"""タスクリポジトリ

タスクデータアクセス層の抽象化
"""

import uuid
from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.core.constants import APIConstants
from app.models.tag import Tag
from app.models.task import Task
from app.models.task_tag import TaskTag
from app.schemas.tag import TagSummary
from app.schemas.task import TaskFilters, TaskListResponse, TaskResponse, TaskSortOptions


class TaskRepositoryInterface(ABC):
    """タスクリポジトリのインターフェース"""

    @abstractmethod
    async def get_by_id(self, db: AsyncSession, task_id: uuid.UUID, user_id: uuid.UUID) -> TaskResponse | None:
        """IDでタスクを取得"""
        pass

    @abstractmethod
    async def get_list(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = APIConstants.DEFAULT_PAGE_SIZE,
        filters: TaskFilters | None = None,
        sort_options: TaskSortOptions | None = None,
    ) -> TaskListResponse:
        """ユーザーのタスク一覧を取得"""
        pass

    @abstractmethod
    async def get_by_status_list(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        status: str,
        *,
        skip: int = 0,
        limit: int = APIConstants.DEFAULT_PAGE_SIZE,
    ) -> list[TaskResponse]:
        """ステータス別でタスクリストを取得"""
        pass

    @abstractmethod
    async def get_overdue_list(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = APIConstants.DEFAULT_PAGE_SIZE,
    ) -> list[TaskResponse]:
        """期限切れタスクリストを取得"""
        pass


class TaskRepository(TaskRepositoryInterface):
    """タスクリポジトリの実装"""

    async def get_by_id(self, db: AsyncSession, task_id: uuid.UUID, user_id: uuid.UUID) -> TaskResponse | None:
        """IDでタスクを取得"""
        # タスクの基本情報を取得
        stmt = select(Task).where(Task.id == task_id, Task.user_id == user_id)
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()

        if not task:
            return None

        # タスクのタグ情報を取得
        tags = await self._get_tags_for_task(db, task_id)

        # Pydanticレスポンスモデルに変換（セッション内）
        task_data: dict[str, Any] = {
            "id": task.id,
            "user_id": task.user_id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "due_date": task.due_date,
            "completed_at": task.completed_at,
            "position": task.position,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "tags": tags,
        }

        return TaskResponse.model_validate(task_data)

    async def get_list(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = APIConstants.DEFAULT_PAGE_SIZE,
        filters: TaskFilters | None = None,
        sort_options: TaskSortOptions | None = None,
    ) -> TaskListResponse:
        """ユーザーのタスク一覧を取得

        パフォーマンスを考慮してバッチ処理で実装
        """
        # ベースクエリ構築
        stmt = select(Task).where(Task.user_id == user_id)

        # フィルタリング適用
        if filters:
            stmt = self._apply_filters(stmt, filters)

        # ソート適用
        stmt = self._apply_sort(stmt, sort_options) if sort_options else stmt.order_by(Task.created_at.desc())

        # 総件数取得（ページネーション用）
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        # ページネーション適用
        stmt = stmt.offset(skip).limit(limit)

        # タスク取得
        result = await db.execute(stmt)
        tasks = list(result.scalars().all())

        if not tasks:
            return TaskListResponse(
                tasks=[],
                total=0,
                page=(skip // limit) + 1,
                per_page=limit,
                total_pages=0,
            )

        # 全タスクのタグ情報を取得
        task_ids = [task.id for task in tasks]
        task_tags_map = await self._get_tags_for_tasks(db, task_ids)

        # Pydanticレスポンスモデルに変換
        task_responses = []
        for task in tasks:
            tags = task_tags_map.get(task.id, [])
            task_data: dict[str, Any] = {
                "id": task.id,
                "user_id": task.user_id,
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "due_date": task.due_date,
                "completed_at": task.completed_at,
                "position": task.position,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "tags": tags,
            }
            task_responses.append(TaskResponse.model_validate(task_data))

        # ページネーション情報計算
        page = (skip // limit) + 1
        total_pages = (total + limit - 1) // limit

        return TaskListResponse(
            tasks=task_responses,
            total=total,
            page=page,
            per_page=limit,
            total_pages=total_pages,
        )

    async def get_by_status_list(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        status: str,
        *,
        skip: int = 0,
        limit: int = APIConstants.DEFAULT_PAGE_SIZE,
    ) -> list[TaskResponse]:
        """ステータス別でタスクリストを取得"""
        stmt = (
            select(Task)
            .where(Task.user_id == user_id, Task.status == status)
            .order_by(Task.position.asc(), Task.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(stmt)
        tasks = list(result.scalars().all())

        if not tasks:
            return []

        # タグ情報を取得
        task_ids = [task.id for task in tasks]
        task_tags_map = await self._get_tags_for_tasks(db, task_ids)

        # Pydanticレスポンスモデルに変換
        task_responses = []
        for task in tasks:
            tags = task_tags_map.get(task.id, [])
            task_data: dict[str, Any] = {
                "id": task.id,
                "user_id": task.user_id,
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "due_date": task.due_date,
                "completed_at": task.completed_at,
                "position": task.position,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "tags": tags,
            }
            task_responses.append(TaskResponse.model_validate(task_data))

        return task_responses

    async def get_overdue_list(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = APIConstants.DEFAULT_PAGE_SIZE,
    ) -> list[TaskResponse]:
        """期限切れタスクリストを取得"""
        from datetime import UTC, datetime

        now = datetime.now(UTC)

        stmt = (
            select(Task)
            .where(
                Task.user_id == user_id,
                Task.due_date < now,
                Task.status != "done",
                Task.status != "archived",
            )
            .order_by(Task.due_date.asc())
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(stmt)
        tasks = list(result.scalars().all())

        if not tasks:
            return []

        # タグ情報を取得
        task_ids = [task.id for task in tasks]
        task_tags_map = await self._get_tags_for_tasks(db, task_ids)

        # Pydanticレスポンスモデルに変換
        task_responses = []
        for task in tasks:
            tags = task_tags_map.get(task.id, [])
            task_data: dict[str, Any] = {
                "id": task.id,
                "user_id": task.user_id,
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "due_date": task.due_date,
                "completed_at": task.completed_at,
                "position": task.position,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "tags": tags,
            }
            task_responses.append(TaskResponse.model_validate(task_data))

        return task_responses

    async def _get_tags_for_task(self, db: AsyncSession, task_id: uuid.UUID) -> list[TagSummary]:
        """単一タスクのタグ情報を取得"""
        stmt = (
            select(Tag)
            .join(TaskTag, Tag.id == TaskTag.tag_id)
            .where(TaskTag.task_id == task_id, Tag.is_active == True)  # noqa: E712
            .order_by(Tag.name)
        )

        result = await db.execute(stmt)
        tags = list(result.scalars().all())

        return [
            TagSummary(
                id=tag.id,
                name=tag.name,
                color=tag.color,
                description=tag.description,
            )
            for tag in tags
        ]

    async def _get_tags_for_tasks(
        self, db: AsyncSession, task_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, list[TagSummary]]:
        """複数タスクのタグ情報を効率的にバッチ取得"""
        if not task_ids:
            return {}

        stmt = (
            select(TaskTag.task_id, Tag)
            .join(Tag, TaskTag.tag_id == Tag.id)
            .where(TaskTag.task_id.in_(task_ids), Tag.is_active == True)  # noqa: E712
            .order_by(TaskTag.task_id, Tag.name)
        )

        result = await db.execute(stmt)
        rows = result.all()

        # 結果をタスクIDでグループ化
        task_tags_map: dict[uuid.UUID, list[TagSummary]] = {}
        for task_id, tag in rows:
            if task_id not in task_tags_map:
                task_tags_map[task_id] = []

            tag_summary = TagSummary(
                id=tag.id,
                name=tag.name,
                color=tag.color,
                description=tag.description,
            )
            task_tags_map[task_id].append(tag_summary)

        # 存在しないタスクIDには空リストを設定
        for task_id in task_ids:
            if task_id not in task_tags_map:
                task_tags_map[task_id] = []

        return task_tags_map

    def _apply_filters(self, stmt: Select[tuple[Task]], filters: TaskFilters) -> Select[tuple[Task]]:
        """フィルタリング条件を適用"""
        if filters.status:
            status_values = [s.value for s in filters.status]
            stmt = stmt.where(Task.status.in_(status_values))

        if filters.priority:
            priority_values = [p.value for p in filters.priority]
            stmt = stmt.where(Task.priority.in_(priority_values))

        if filters.due_date_from:
            stmt = stmt.where(Task.due_date >= filters.due_date_from)
        if filters.due_date_to:
            stmt = stmt.where(Task.due_date <= filters.due_date_to)

        if filters.is_overdue is not None:
            from datetime import UTC, datetime

            now = datetime.now(UTC)
            if filters.is_overdue:
                stmt = stmt.where(Task.due_date < now, Task.status != "done")
            else:
                stmt = stmt.where((Task.due_date >= now) | (Task.due_date.is_(None)) | (Task.status == "done"))

        if filters.tag_ids or filters.tag_names:
            stmt = stmt.join(TaskTag, Task.id == TaskTag.task_id)

            if filters.tag_ids:
                stmt = stmt.where(TaskTag.tag_id.in_(filters.tag_ids))

            if filters.tag_names:
                stmt = stmt.join(Tag, TaskTag.tag_id == Tag.id)
                stmt = stmt.where(Tag.name.in_(filters.tag_names))

        if filters.search:
            search_term = f"%{filters.search}%"
            stmt = stmt.where(Task.title.ilike(search_term) | Task.description.ilike(search_term))

        return stmt

    def _apply_sort(self, stmt: Select[tuple[Task]], sort_options: TaskSortOptions) -> Select[tuple[Task]]:
        """ソート条件を適用"""
        sort_field = getattr(Task, sort_options.sort_by, None)
        if sort_field is None:
            # フィールドが存在しない場合はデフォルトソート
            return stmt.order_by(Task.created_at.desc())

        if sort_options.order == "desc":
            return stmt.order_by(sort_field.desc())
        else:
            return stmt.order_by(sort_field.asc())


# シングルトンインスタンス
task_repository = TaskRepository()
