"""TaskTag リポジトリ

TaskTag のデータアクセス層の抽象化
"""

import uuid
from abc import ABC, abstractmethod

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task_tag import TaskTag


class TaskTagRepositoryInterface(ABC):
    """TaskTag リポジトリのインターフェース"""

    @abstractmethod
    async def get_by_id(self, db: AsyncSession, task_tag_id: uuid.UUID) -> TaskTag | None:
        """IDでTaskTagを取得"""
        pass

    @abstractmethod
    async def get_by_task_and_tag(self, db: AsyncSession, task_id: uuid.UUID, tag_id: uuid.UUID) -> TaskTag | None:
        """タスクIDとタグIDでTaskTagを取得"""
        pass


class TaskTagRepository(TaskTagRepositoryInterface):
    """TaskTag リポジトリの実装"""

    async def get_by_id(self, db: AsyncSession, task_tag_id: uuid.UUID) -> TaskTag | None:
        """IDでTaskTagを取得

        Args:
            db: データベースセッション
            task_tag_id: TaskTagのID

        Returns:
            TaskTagインスタンスまたはNone
        """
        result = await db.execute(select(TaskTag).where(TaskTag.id == task_tag_id))
        return result.scalar_one_or_none()

    async def get_by_task_and_tag(self, db: AsyncSession, task_id: uuid.UUID, tag_id: uuid.UUID) -> TaskTag | None:
        """タスクIDとタグIDでTaskTagを取得

        Args:
            db: データベースセッション
            task_id: タスクID
            tag_id: タグID

        Returns:
            TaskTagインスタンスまたはNone
        """
        result = await db.execute(select(TaskTag).where(TaskTag.task_id == task_id, TaskTag.tag_id == tag_id))
        return result.scalar_one_or_none()

    async def get_with_relations(self, db: AsyncSession, task_tag_id: uuid.UUID) -> dict | None:
        """関連情報を含むTaskTagデータを取得

        Args:
            db: データベースセッション
            task_tag_id: TaskTagのID

        Returns:
            TaskTag辞書データまたはNone
        """
        result = await db.execute(
            select(TaskTag)
            .options(selectinload(TaskTag.task), selectinload(TaskTag.tag))
            .where(TaskTag.id == task_tag_id)
        )
        task_tag = result.scalar_one_or_none()

        if not task_tag:
            return None

        # 安全に計算プロパティを使用
        return self._convert_to_dict(task_tag)

    async def get_multiple_with_relations(self, db: AsyncSession, task_tag_ids: list[uuid.UUID]) -> list[dict]:
        """複数のTaskTagを関連情報込みで取得

        Args:
            db: データベースセッション
            task_tag_ids: TaskTagのIDリスト

        Returns:
            TaskTag辞書データのリスト
        """
        if not task_tag_ids:
            return []

        result = await db.execute(
            select(TaskTag)
            .options(selectinload(TaskTag.task), selectinload(TaskTag.tag))
            .where(TaskTag.id.in_(task_tag_ids))
        )
        task_tags = result.scalars().all()

        return [self._convert_to_dict(task_tag) for task_tag in task_tags]

    async def get_by_task_with_relations(self, db: AsyncSession, task_id: uuid.UUID) -> list[dict]:
        """タスクに関連するTaskTagを関連情報込みで取得

        Args:
            db: データベースセッション
            task_id: タスクID

        Returns:
            TaskTag辞書データのリスト
        """
        result = await db.execute(
            select(TaskTag)
            .options(selectinload(TaskTag.task), selectinload(TaskTag.tag))
            .where(TaskTag.task_id == task_id)
        )
        task_tags = result.scalars().all()

        return [self._convert_to_dict(task_tag) for task_tag in task_tags]

    async def get_by_tag_with_relations(self, db: AsyncSession, tag_id: uuid.UUID) -> list[dict]:
        """タグに関連するTaskTagを関連情報込みで取得

        Args:
            db: データベースセッション
            tag_id: タグID

        Returns:
            TaskTag辞書データのリスト
        """
        result = await db.execute(
            select(TaskTag)
            .options(selectinload(TaskTag.task), selectinload(TaskTag.tag))
            .where(TaskTag.tag_id == tag_id)
        )
        task_tags = result.scalars().all()

        return [self._convert_to_dict(task_tag) for task_tag in task_tags]

    def _convert_to_dict(self, task_tag: TaskTag) -> dict:
        """TaskTagを辞書形式に変換

        Args:
            task_tag: TaskTagインスタンス（リレーション事前読み込み済み）

        Returns:
            TaskTag辞書データ
        """
        return {
            "id": task_tag.id,
            "task_id": task_tag.task_id,
            "tag_id": task_tag.tag_id,
            "created_at": task_tag.created_at,
            "updated_at": task_tag.updated_at,
            "task_info": task_tag.task_display_info,
            "tag_info": task_tag.tag_display_info,
            "is_task_completed": task_tag.is_task_completed(),
            "is_task_archived": task_tag.is_task_archived(),
            "is_tag_active": task_tag.is_tag_active(),
            "task_status": task_tag.task_status,
            "task_priority": task_tag.task_priority,
        }


# シングルトンインスタンス
task_tag_repository = TaskTagRepository()
