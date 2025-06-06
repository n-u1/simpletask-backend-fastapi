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
from app.utils.pagination import calculate_pagination, create_pagination_result


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
        from app.utils.permission import ensure_resource_access

        ensure_resource_access(task, user_id, "タスク")

        return task

    async def get_tasks(
        self,
        db: AsyncSession,
        user_id: UUID,
        *,
        page: int = 1,
        per_page: int = APIConstants.DEFAULT_PAGE_SIZE,
        filters: TaskFilters | None = None,
        sort_options: TaskSortOptions | None = None,
    ) -> TaskListResponse:
        """タスク一覧を取得"""
        # ページネーション計算
        pagination_params = calculate_pagination(page, per_page)

        # タスク取得
        tasks = await self.task_crud.get_multi_by_user(
            db,
            user_id,
            skip=pagination_params.skip,
            limit=pagination_params.limit,
            filters=filters,
            sort_options=sort_options,
        )

        # 総件数取得
        total = await self.task_crud.count_by_user(db, user_id, filters)

        # ページネーション結果作成
        pagination_result = create_pagination_result(pagination_params.page, pagination_params.limit, total)

        return TaskListResponse(
            tasks=[TaskResponse.model_validate(task) for task in tasks],
            total=pagination_result.total,
            page=pagination_result.page,
            per_page=pagination_result.per_page,
            total_pages=pagination_result.total_pages,
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
        page: int = 1,
        per_page: int = APIConstants.DEFAULT_PAGE_SIZE,
    ) -> list[Task]:
        """ステータス別でタスクを取得"""
        # ページネーション計算
        pagination_params = calculate_pagination(page, per_page)

        tasks = await self.task_crud.get_by_status(
            db, user_id, status, skip=pagination_params.skip, limit=pagination_params.limit
        )

        return tasks

    async def get_overdue_tasks(
        self,
        db: AsyncSession,
        user_id: UUID,
        *,
        page: int = 1,
        per_page: int = APIConstants.DEFAULT_PAGE_SIZE,
    ) -> list[Task]:
        """期限切れタスクを取得"""
        # ページネーション計算
        pagination_params = calculate_pagination(page, per_page)

        tasks = await self.task_crud.get_overdue_tasks(
            db, user_id, skip=pagination_params.skip, limit=pagination_params.limit
        )

        return tasks

    async def _validate_tag_ownership(self, db: AsyncSession, tag_ids: list[UUID], user_id: UUID) -> None:
        """タグの所有権を検証"""
        from app.utils.permission import create_permission_checker

        permission_checker = create_permission_checker(user_id)

        # 利用可能なタグを一括取得
        available_tags = []
        for tag_id in tag_ids:
            tag = await self.tag_crud.get_by_user(db, user_id, tag_id)
            if tag:
                available_tags.append(tag)

        # 一括権限チェック
        permission_checker.validate_tag_ownership_list(tag_ids, available_tags)


task_service = TaskService()
