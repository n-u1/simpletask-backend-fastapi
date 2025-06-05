"""タスクサービス層

タスクのビジネスロジックを提供
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import APIConstants, ErrorMessages, TaskStatus
from app.crud.tag import tag_crud
from app.crud.task import task_crud
from app.models.task import Task
from app.schemas.task import (
    TaskCreate,
    TaskFilters,
    TaskListResponse,
    TaskPositionUpdate,
    TaskResponse,
    TaskSortOptions,
    TaskUpdate,
)


class TaskService:
    def __init__(self) -> None:
        self.task_crud = task_crud
        self.tag_crud = tag_crud

    async def get_task(self, db: AsyncSession, task_id: UUID, user_id: UUID) -> Task | None:
        """タスクを取得"""
        task = await self.task_crud.get_by_user(db, user_id, task_id)
        if not task:
            return None

        # アクセス権限チェック
        if task.user_id != user_id:
            raise PermissionError(ErrorMessages.TASK_ACCESS_DENIED)

        return task

    async def get_tasks(
        self,
        db: AsyncSession,
        user_id: UUID,
        *,
        skip: int = 0,
        limit: int = APIConstants.DEFAULT_PAGE_SIZE,
        filters: TaskFilters | None = None,
        sort_options: TaskSortOptions | None = None,
    ) -> TaskListResponse:
        """タスク一覧を取得"""
        # 制限値チェック
        limit = min(limit, APIConstants.MAX_PAGE_SIZE)
        limit = max(limit, APIConstants.MIN_PAGE_SIZE)

        # タスク取得
        tasks = await self.task_crud.get_multi_by_user(
            db, user_id, skip=skip, limit=limit, filters=filters, sort_options=sort_options
        )

        # 総件数取得
        total = await self.task_crud.count_by_user(db, user_id, filters)

        # ページネーション計算
        page = (skip // limit) + 1
        total_pages = (total + limit - 1) // limit

        return TaskListResponse(
            tasks=[TaskResponse.model_validate(task) for task in tasks],
            total=total,
            page=page,
            per_page=limit,
            total_pages=total_pages,
        )

    async def create_task(self, db: AsyncSession, task_in: TaskCreate, user_id: UUID) -> Task:
        """タスクを作成"""
        # タグの存在確認
        if task_in.tag_ids:
            await self._validate_tag_ownership(db, task_in.tag_ids, user_id)

        task = await self.task_crud.create_with_tags(db, task_in=task_in, user_id=user_id)

        return task

    async def update_task(self, db: AsyncSession, task_id: UUID, task_in: TaskUpdate, user_id: UUID) -> Task:
        """タスクを更新"""
        # タスク取得と権限チェック
        task = await self.get_task(db, task_id, user_id)
        if not task:
            raise ValueError(ErrorMessages.TASK_NOT_FOUND)

        # タグの存在確認
        if task_in.tag_ids is not None:
            await self._validate_tag_ownership(db, task_in.tag_ids, user_id)

        updated_task = await self.task_crud.update_with_tags(db, db_task=task, task_in=task_in)

        return updated_task

    async def update_task_status(self, db: AsyncSession, task_id: UUID, status: TaskStatus, user_id: UUID) -> Task:
        """タスクのステータスを更新"""
        # タスク取得と権限チェック
        task = await self.get_task(db, task_id, user_id)
        if not task:
            raise ValueError(ErrorMessages.TASK_NOT_FOUND)

        updated_task = await self.task_crud.update_status(db, db_task=task, status=status)

        return updated_task

    async def delete_task(self, db: AsyncSession, task_id: UUID, user_id: UUID) -> bool:
        """タスクを削除"""
        # タスク取得と権限チェック
        task = await self.get_task(db, task_id, user_id)
        if not task:
            raise ValueError(ErrorMessages.TASK_NOT_FOUND)

        deleted_task = await self.task_crud.delete(db, id=task_id)
        return deleted_task is not None

    async def reorder_tasks(self, db: AsyncSession, position_update: TaskPositionUpdate, user_id: UUID) -> bool:
        """タスクの並び順を変更（ドラッグ&ドロップ用）"""
        # メインタスクの権限チェック
        main_task = await self.get_task(db, position_update.task_id, user_id)
        if not main_task:
            raise ValueError(ErrorMessages.TASK_NOT_FOUND)

        # 位置更新データの準備
        position_updates = []

        # メインタスクの更新データ
        main_update = {"id": position_update.task_id, "position": position_update.new_position}
        if position_update.new_status:
            main_update["status"] = position_update.new_status.value

        position_updates.append(main_update)

        # 影響を受ける他のタスクの更新データ
        for affected_task in position_update.affected_tasks:
            # タスクの所有権確認
            task = await self.get_task(db, affected_task.id, user_id)
            if task:
                position_updates.append({"id": affected_task.id, "position": affected_task.position})

        # 一括位置更新
        success = await self.task_crud.update_positions(db, position_updates=position_updates, user_id=user_id)

        return success

    async def get_tasks_by_status(
        self,
        db: AsyncSession,
        user_id: UUID,
        status: TaskStatus,
        *,
        skip: int = 0,
        limit: int = APIConstants.DEFAULT_PAGE_SIZE,
    ) -> list[Task]:
        """ステータス別でタスクを取得"""
        limit = min(limit, APIConstants.MAX_PAGE_SIZE)

        tasks = await self.task_crud.get_by_status(db, user_id, status, skip=skip, limit=limit)

        return tasks

    async def get_overdue_tasks(
        self, db: AsyncSession, user_id: UUID, *, skip: int = 0, limit: int = APIConstants.DEFAULT_PAGE_SIZE
    ) -> list[Task]:
        """期限切れタスクを取得"""
        limit = min(limit, APIConstants.MAX_PAGE_SIZE)

        tasks = await self.task_crud.get_overdue_tasks(db, user_id, skip=skip, limit=limit)

        return tasks

    async def _validate_tag_ownership(self, db: AsyncSession, tag_ids: list[UUID], user_id: UUID) -> None:
        """タグの所有権を検証"""
        for tag_id in tag_ids:
            tag = await self.tag_crud.get_by_user(db, user_id, tag_id)
            if not tag:
                raise ValueError(f"タグ（ID: {tag_id}）が見つかりません")
            if not tag.is_active:
                raise ValueError(f"タグ「{tag.name}」は無効化されています")


task_service = TaskService()
