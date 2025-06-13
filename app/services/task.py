"""タスクサービス層

タスクのビジネスロジックを提供
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import APIConstants, ErrorMessages, TaskStatus
from app.crud.task import task_crud
from app.models.task import Task
from app.repositories.task import task_repository
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
        self.task_repository = task_repository

    async def get_task(self, db: AsyncSession, task_id: UUID, user_id: UUID) -> Task | None:
        """タスクを取得（内部処理用）"""
        task = await self.task_crud.get_by_user(db, user_id, task_id)
        if not task:
            return None

        # アクセス権限チェック
        from app.utils.permission import create_permission_checker

        permission_checker = create_permission_checker(user_id)
        permission_checker.check_task_access(task)

        return task

    async def get_task_for_response(self, db: AsyncSession, task_id: UUID, user_id: UUID) -> dict | None:
        """タスクを取得（API レスポンス用）"""
        task = await self.get_task(db, task_id, user_id)
        if not task:
            return None

        return await self.task_repository.get_with_tag_info(db, task_id, user_id)

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

        # タグ情報込みでタスクデータを変換
        task_dicts = await self.task_repository.get_multiple_with_tag_info(db, tasks)

        return TaskListResponse(
            tasks=[TaskResponse(**task_dict) for task_dict in task_dicts],
            total=pagination_result.total,
            page=pagination_result.page,
            per_page=pagination_result.per_page,
            total_pages=pagination_result.total_pages,
        )

    async def create_task(self, db: AsyncSession, task_in: TaskCreate, user_id: UUID) -> Task:
        """タスクを作成（内部処理用）"""
        try:
            task = await self.task_crud.create_with_tags(db, task_in=task_in, user_id=user_id)
            return task

        except ValueError as e:
            raise ValueError(str(e)) from e

    async def create_task_for_response(self, db: AsyncSession, task_in: TaskCreate, user_id: UUID) -> dict:
        """タスクを作成（API レスポンス用）"""
        try:
            task = await self.task_crud.create_with_tags(db, task_in=task_in, user_id=user_id)

            return await self.task_repository.create_with_response_data(task)

        except ValueError as e:
            raise ValueError(str(e)) from e

    async def update_task(self, db: AsyncSession, task_id: UUID, task_in: TaskUpdate, user_id: UUID) -> Task:
        """タスクを更新（内部処理用）"""
        # タスク取得と権限チェック
        task = await self.get_task(db, task_id, user_id)
        if not task:
            raise ValueError(ErrorMessages.TASK_NOT_FOUND)

        try:
            updated_task = await self.task_crud.update_with_tags(db, db_task=task, task_in=task_in)
            return updated_task

        except ValueError as e:
            raise ValueError(str(e)) from e

    async def update_task_for_response(
        self, db: AsyncSession, task_id: UUID, task_in: TaskUpdate, user_id: UUID
    ) -> dict:
        """タスクを更新（API レスポンス用）"""
        await self.update_task(db, task_id, task_in, user_id)

        task_data = await self.task_repository.get_with_tag_info(db, task_id, user_id)
        if task_data is None:
            raise ValueError(ErrorMessages.TASK_NOT_FOUND)

        return task_data

    async def update_task_status(self, db: AsyncSession, task_id: UUID, status: TaskStatus, user_id: UUID) -> Task:
        """タスクステータスを更新（内部処理用）"""
        # タスク取得と権限チェック
        task = await self.get_task(db, task_id, user_id)
        if not task:
            raise ValueError(ErrorMessages.TASK_NOT_FOUND)

        try:
            updated_task = await self.task_crud.update_status(db, db_task=task, status=status)
            return updated_task

        except ValueError as e:
            raise ValueError(str(e)) from e

    async def update_task_status_for_response(
        self, db: AsyncSession, task_id: UUID, status: TaskStatus, user_id: UUID
    ) -> dict:
        """タスクステータスを更新（API レスポンス用）"""
        await self.update_task_status(db, task_id, status, user_id)

        task_data = await self.task_repository.get_with_tag_info(db, task_id, user_id)
        if task_data is None:
            raise ValueError(ErrorMessages.TASK_NOT_FOUND)

        return task_data

    async def delete_task(self, db: AsyncSession, task_id: UUID, user_id: UUID) -> bool:
        """タスクを削除"""
        # タスク取得と権限チェック
        task = await self.get_task(db, task_id, user_id)
        if not task:
            raise ValueError(ErrorMessages.TASK_NOT_FOUND)

        try:
            success = await self.task_crud.delete(db, id=task_id)
            return success is not None

        except ValueError as e:
            raise ValueError(str(e)) from e

    async def get_tasks_by_status(
        self, db: AsyncSession, user_id: UUID, status: TaskStatus, *, page: int = 1, per_page: int = 20
    ) -> list[Task]:
        """ステータス別でタスクを取得（内部処理用）"""
        try:
            # ページネーション計算
            skip = (page - 1) * per_page
            tasks = await self.task_crud.get_by_status(db, user_id, status, skip=skip, limit=per_page)
            return tasks

        except ValueError as e:
            raise ValueError(str(e)) from e

    async def get_tasks_by_status_for_response(
        self, db: AsyncSession, user_id: UUID, status: TaskStatus, *, page: int = 1, per_page: int = 20
    ) -> list[dict]:
        """ステータス別でタスクを取得（API レスポンス用）"""
        tasks = await self.get_tasks_by_status(db, user_id, status, page=page, per_page=per_page)

        # タグ情報込みでデータ変換
        return await self.task_repository.get_multiple_with_tag_info(db, tasks)

    async def get_overdue_tasks(
        self, db: AsyncSession, user_id: UUID, *, page: int = 1, per_page: int = 20
    ) -> list[Task]:
        """期限切れタスクを取得（内部処理用）"""
        try:
            # ページネーション計算
            skip = (page - 1) * per_page
            tasks = await self.task_crud.get_overdue_tasks(db, user_id, skip=skip, limit=per_page)
            return tasks

        except ValueError as e:
            raise ValueError(str(e)) from e

    async def get_overdue_tasks_for_response(
        self, db: AsyncSession, user_id: UUID, *, page: int = 1, per_page: int = 20
    ) -> list[dict]:
        """期限切れタスクを取得（API レスポンス用）"""
        tasks = await self.get_overdue_tasks(db, user_id, page=page, per_page=per_page)

        # タグ情報込みでデータ変換
        return await self.task_repository.get_multiple_with_tag_info(db, tasks)

    async def reorder_tasks(self, db: AsyncSession, position_update: TaskPositionUpdate, user_id: UUID) -> bool:
        """タスクの並び順を変更（ドラッグ&ドロップ用）"""
        try:
            # 1. 移動対象タスクの存在確認と権限チェック
            target_task = await self.get_task(db, position_update.task_id, user_id)
            if not target_task:
                raise ValueError(ErrorMessages.TASK_NOT_FOUND)

            # 2. 移動前後の状態を取得
            old_status = target_task.status
            old_position = target_task.position
            new_status = position_update.new_status.value if position_update.new_status else old_status
            new_position = position_update.new_position

            # 3. 同じ位置への移動は無視
            if old_status == new_status and old_position == new_position:
                return True

            # 4. 影響を受けるタスクの位置更新を自動計算
            position_updates = await self._calculate_position_updates(
                db, user_id, position_update.task_id, old_status, old_position, new_status, new_position
            )

            # 5. 一括更新実行
            success = await self.task_crud.update_positions(
                db,
                position_updates=position_updates,
                user_id=user_id,
            )

            return success

        except ValueError as e:
            raise ValueError(str(e)) from e

    async def _calculate_position_updates(
        self,
        db: AsyncSession,
        user_id: UUID,
        target_task_id: UUID,
        old_status: str,
        old_position: int,
        new_status: str,
        new_position: int,
    ) -> list[dict[str, UUID | str | int | None]]:
        """位置更新を自動計算（ドラッグ&ドロップ用）"""
        position_updates: list[dict[str, UUID | str | int | None]] = []

        # メインタスクの更新
        main_update: dict[str, UUID | str | int | None] = {
            "id": target_task_id,
            "position": new_position,
            "status": new_status if new_status != old_status else None,
        }
        position_updates.append(main_update)

        # ステータス変更（カンバン間移動）の場合
        if new_status != old_status:
            # 元のステータスグループ：抜けた位置より後のタスクを前に詰める
            old_status_tasks = await self.task_crud.get_by_status(db, user_id, TaskStatus(old_status))
            for task in old_status_tasks:
                if task.id != target_task_id and task.position > old_position:
                    old_status_update: dict[str, UUID | str | int | None] = {
                        "id": task.id,
                        "position": task.position - 1,
                        "status": None,
                    }
                    position_updates.append(old_status_update)

            # 新しいステータスグループ：挿入位置以降のタスクを後ろに移動
            new_status_tasks = await self.task_crud.get_by_status(db, user_id, TaskStatus(new_status))
            for task in new_status_tasks:
                if task.position >= new_position:
                    new_status_update: dict[str, UUID | str | int | None] = {
                        "id": task.id,
                        "position": task.position + 1,
                        "status": None,
                    }
                    position_updates.append(new_status_update)

        # 同一ステータス内での移動の場合
        else:
            same_status_tasks = await self.task_crud.get_by_status(db, user_id, TaskStatus(old_status))

            if new_position > old_position:
                # 下に移動：間のタスクを上に詰める
                for task in same_status_tasks:
                    if task.id != target_task_id and old_position < task.position <= new_position:
                        move_up_update: dict[str, UUID | str | int | None] = {
                            "id": task.id,
                            "position": task.position - 1,
                            "status": None,
                        }
                        position_updates.append(move_up_update)
            elif new_position < old_position:
                # 上に移動：間のタスクを下に移動
                for task in same_status_tasks:
                    if task.id != target_task_id and new_position <= task.position < old_position:
                        move_down_update: dict[str, UUID | str | int | None] = {
                            "id": task.id,
                            "position": task.position + 1,
                            "status": None,
                        }
                        position_updates.append(move_down_update)

        return position_updates


task_service = TaskService()
