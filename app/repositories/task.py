"""タスクリポジトリ

タスクデータアクセス層の抽象化
"""

import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.models.task import Task


class TaskRepositoryInterface(ABC):
    """タスクリポジトリのインターフェース"""

    @abstractmethod
    async def get_by_id(self, db: AsyncSession, task_id: uuid.UUID) -> Optional["Task"]:
        """IDでタスクを取得"""
        pass

    @abstractmethod
    async def get_by_user(self, db: AsyncSession, user_id: uuid.UUID, task_id: uuid.UUID) -> Optional["Task"]:
        """ユーザーIDとタスクIDでタスクを取得"""
        pass

    @abstractmethod
    async def get_user_tasks(
        self, db: AsyncSession, user_id: uuid.UUID, skip: int = 0, limit: int = 20
    ) -> list["Task"]:
        """ユーザーのタスク一覧を取得"""
        pass


class TaskRepository(TaskRepositoryInterface):
    """タスクリポジトリの実装"""

    async def get_by_id(self, db: AsyncSession, task_id: uuid.UUID) -> Optional["Task"]:
        """IDでタスクを取得

        Args:
            db: データベースセッション
            task_id: タスクID

        Returns:
            タスクインスタンスまたはNone
        """
        from app.crud.task import task_crud

        return await task_crud.get(db, id=task_id)

    async def get_by_user(self, db: AsyncSession, user_id: uuid.UUID, task_id: uuid.UUID) -> Optional["Task"]:
        """ユーザーIDとタスクIDでタスクを取得

        Args:
            db: データベースセッション
            user_id: ユーザーID
            task_id: タスクID

        Returns:
            タスクインスタンスまたはNone
        """
        from app.crud.task import task_crud

        return await task_crud.get_by_user(db, user_id=user_id, task_id=task_id)

    async def get_user_tasks(
        self, db: AsyncSession, user_id: uuid.UUID, skip: int = 0, limit: int = 20
    ) -> list["Task"]:
        """ユーザーのタスク一覧を取得

        Args:
            db: データベースセッション
            user_id: ユーザーID
            skip: スキップ件数
            limit: 取得件数

        Returns:
            タスクインスタンスのリスト
        """
        from app.crud.task import task_crud

        return await task_crud.get_multi_by_user(db, user_id=user_id, skip=skip, limit=limit)


# シングルトンインスタンス
task_repository = TaskRepository()
