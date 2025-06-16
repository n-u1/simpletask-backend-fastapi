"""タスクサービス層

タスクのビジネスロジックを提供
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import APIConstants, ErrorMessages, TaskStatus
from app.crud.task import task_crud
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


class TaskService:
    """タスクサービス

    ビジネスロジックのみに専念
    データ変換はリポジトリ層で実施
    """

    def __init__(self) -> None:
        self.task_crud = task_crud
        self.task_repository = task_repository

    async def get_task(self, db: AsyncSession, task_id: UUID, user_id: UUID) -> TaskResponse | None:
        """タスクを取得

        Args:
            db: データベースセッション
            task_id: タスクID
            user_id: ユーザーID

        Returns:
            TaskResponse または None

        Raises:
            PermissionError: アクセス権限がない場合
        """
        # Pydanticレスポンスモデルで取得
        task_response = await self.task_repository.get_by_id(db, task_id, user_id)
        if not task_response:
            return None

        # アクセス権限チェック
        if task_response.user_id != user_id:
            raise PermissionError(ErrorMessages.TASK_ACCESS_DENIED)

        return task_response

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
        """タスク一覧を取得

        Args:
            db: データベースセッション
            user_id: ユーザーID
            page: ページ番号
            per_page: 1ページあたりの件数
            filters: フィルタ条件
            sort_options: ソート条件

        Returns:
            TaskListResponse
        """
        # ページネーション計算
        skip = (page - 1) * per_page

        # リポジトリから取得
        return await self.task_repository.get_list(
            db,
            user_id,
            skip=skip,
            limit=per_page,
            filters=filters,
            sort_options=sort_options,
        )

    async def create_task(self, db: AsyncSession, task_in: TaskCreate, user_id: UUID) -> TaskResponse:
        """タスクを作成

        Args:
            db: データベースセッション
            task_in: タスク作成データ
            user_id: ユーザーID

        Returns:
            作成されたTaskResponse

        Raises:
            ValueError: バリデーションエラー
        """
        try:
            # タグIDの検証は行わない（CRUDレイヤーで有効なタグのみ関連付け）
            # 存在しないタグや他ユーザーのタグは無視される

            # タスク作成
            task = await self.task_crud.create_with_tags(db, task_in=task_in, user_id=user_id)

            # Pydanticレスポンスモデルで取得して返却
            created_task_response = await self.task_repository.get_by_id(db, task.id, user_id)
            if not created_task_response:
                raise ValueError("タスクの作成に失敗しました")

            return created_task_response

        except ValueError as e:
            raise ValueError(str(e)) from e

    async def update_task(self, db: AsyncSession, task_id: UUID, task_in: TaskUpdate, user_id: UUID) -> TaskResponse:
        """タスクを更新

        Args:
            db: データベースセッション
            task_id: タスクID
            task_in: タスク更新データ
            user_id: ユーザーID

        Returns:
            更新されたTaskResponse

        Raises:
            ValueError: タスクが見つからない場合やバリデーションエラー
            PermissionError: アクセス権限がない場合
        """
        # タスク取得と権限チェック
        existing_task_response = await self.get_task(db, task_id, user_id)
        if not existing_task_response:
            raise ValueError(ErrorMessages.TASK_NOT_FOUND)

        # タグIDの検証は行わない（CRUDレイヤーで有効なタグのみ関連付け）

        # CRUDレイヤーで更新処理（SQLAlchemyモデルが必要）
        task = await self.task_crud.get_by_user(db, user_id, task_id)
        if not task:
            raise ValueError(ErrorMessages.TASK_NOT_FOUND)

        try:
            await self.task_crud.update_with_tags(db, db_task=task, task_in=task_in)

            # 更新後のPydanticレスポンスモデルを取得して返却
            updated_task_response = await self.task_repository.get_by_id(db, task_id, user_id)
            if not updated_task_response:
                raise ValueError("タスクの更新に失敗しました")

            return updated_task_response

        except ValueError as e:
            raise ValueError(str(e)) from e

    async def update_task_status(
        self, db: AsyncSession, task_id: UUID, status: TaskStatus, user_id: UUID
    ) -> TaskResponse:
        """タスクステータスを更新

        Args:
            db: データベースセッション
            task_id: タスクID
            status: 新しいステータス
            user_id: ユーザーID

        Returns:
            更新されたTaskResponse

        Raises:
            ValueError: タスクが見つからない場合
            PermissionError: アクセス権限がない場合
        """
        # タスク取得と権限チェック
        existing_task_response = await self.get_task(db, task_id, user_id)
        if not existing_task_response:
            raise ValueError(ErrorMessages.TASK_NOT_FOUND)

        # CRUDレイヤーでステータス更新処理
        task = await self.task_crud.get_by_user(db, user_id, task_id)
        if not task:
            raise ValueError(ErrorMessages.TASK_NOT_FOUND)

        try:
            await self.task_crud.update_status(db, db_task=task, status=status)

            # 更新後のPydanticレスポンスモデルを取得して返却
            updated_task_response = await self.task_repository.get_by_id(db, task_id, user_id)
            if not updated_task_response:
                raise ValueError("タスクステータスの更新に失敗しました")

            return updated_task_response

        except ValueError as e:
            raise ValueError(str(e)) from e

    async def delete_task(self, db: AsyncSession, task_id: UUID, user_id: UUID) -> bool:
        """タスクを削除

        Args:
            db: データベースセッション
            task_id: タスクID
            user_id: ユーザーID

        Returns:
            削除成功フラグ

        Raises:
            ValueError: タスクが見つからない場合
            PermissionError: アクセス権限がない場合
        """
        # タスク取得と権限チェック
        task_response = await self.get_task(db, task_id, user_id)
        if not task_response:
            raise ValueError(ErrorMessages.TASK_NOT_FOUND)

        try:
            success = await self.task_crud.delete(db, id=task_id)
            return success is not None

        except ValueError as e:
            raise ValueError(str(e)) from e

    async def get_tasks_by_status(
        self,
        db: AsyncSession,
        user_id: UUID,
        status: TaskStatus,
        *,
        page: int = 1,
        per_page: int = APIConstants.DEFAULT_PAGE_SIZE,
    ) -> list[TaskResponse]:
        """ステータス別でタスクを取得

        Args:
            db: データベースセッション
            user_id: ユーザーID
            status: タスクステータス
            page: ページ番号
            per_page: 1ページあたりの件数

        Returns:
            TaskResponseのリスト
        """
        try:
            # ページネーション計算
            skip = (page - 1) * per_page
            return await self.task_repository.get_by_status_list(db, user_id, status.value, skip=skip, limit=per_page)

        except ValueError as e:
            raise ValueError(str(e)) from e

    async def get_overdue_tasks(
        self, db: AsyncSession, user_id: UUID, *, page: int = 1, per_page: int = APIConstants.DEFAULT_PAGE_SIZE
    ) -> list[TaskResponse]:
        """期限切れタスクを取得

        Args:
            db: データベースセッション
            user_id: ユーザーID
            page: ページ番号
            per_page: 1ページあたりの件数

        Returns:
            TaskResponseのリスト
        """
        try:
            # ページネーション計算
            skip = (page - 1) * per_page
            return await self.task_repository.get_overdue_list(db, user_id, skip=skip, limit=per_page)

        except ValueError as e:
            raise ValueError(str(e)) from e

    async def reorder_tasks(self, db: AsyncSession, position_update: TaskPositionUpdate, user_id: UUID) -> bool:
        """タスクの並び順を変更（ドラッグ&ドロップ用）

        Args:
            db: データベースセッション
            position_update: 位置更新データ
            user_id: ユーザーID

        Returns:
            更新成功フラグ

        Raises:
            ValueError: タスクが見つからない場合や更新エラー
            PermissionError: アクセス権限がない場合
        """
        try:
            # 移動対象タスクの存在確認と権限チェック
            target_task_response = await self.get_task(db, position_update.task_id, user_id)
            if not target_task_response:
                raise ValueError(ErrorMessages.TASK_NOT_FOUND)

            # 移動前後の状態を取得
            old_status = target_task_response.status.value
            old_position = target_task_response.position
            new_status = position_update.new_status.value if position_update.new_status else old_status
            new_position = position_update.new_position

            # 同じ位置への移動は無視
            if old_status == new_status and old_position == new_position:
                return True

            # 影響を受けるタスクの位置更新を自動計算
            position_updates = await self._calculate_position_updates(
                db, user_id, position_update.task_id, old_status, old_position, new_status, new_position
            )

            # 一括更新実行
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
            old_status_tasks = await self.task_repository.get_by_status_list(
                db, user_id, old_status, skip=0, limit=1000
            )
            for task_response in old_status_tasks:
                if task_response.id != target_task_id and task_response.position > old_position:
                    old_status_update: dict[str, UUID | str | int | None] = {
                        "id": task_response.id,
                        "position": task_response.position - 1,
                        "status": None,
                    }
                    position_updates.append(old_status_update)

            # 新しいステータスグループ：挿入位置以降のタスクを後ろに移動
            new_status_tasks = await self.task_repository.get_by_status_list(
                db, user_id, new_status, skip=0, limit=1000
            )
            for task_response in new_status_tasks:
                if task_response.position >= new_position:
                    new_status_update: dict[str, UUID | str | int | None] = {
                        "id": task_response.id,
                        "position": task_response.position + 1,
                        "status": None,
                    }
                    position_updates.append(new_status_update)

        # 同一ステータス内での移動の場合
        else:
            same_status_tasks = await self.task_repository.get_by_status_list(
                db, user_id, old_status, skip=0, limit=1000
            )

            if new_position > old_position:
                # 下に移動：間のタスクを上に詰める
                for task_response in same_status_tasks:
                    if task_response.id != target_task_id and old_position < task_response.position <= new_position:
                        move_up_update: dict[str, UUID | str | int | None] = {
                            "id": task_response.id,
                            "position": task_response.position - 1,
                            "status": None,
                        }
                        position_updates.append(move_up_update)
            elif new_position < old_position:
                # 上に移動：間のタスクを下に移動
                for task_response in same_status_tasks:
                    if task_response.id != target_task_id and new_position <= task_response.position < old_position:
                        move_down_update: dict[str, UUID | str | int | None] = {
                            "id": task_response.id,
                            "position": task_response.position + 1,
                            "status": None,
                        }
                        position_updates.append(move_down_update)

        return position_updates


# シングルトンインスタンス
task_service = TaskService()
