"""タグリポジトリ

タグデータアクセス層の抽象化
"""

import uuid
from abc import ABC, abstractmethod
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.tag import Tag


class TagRepositoryInterface(ABC):
    """タグリポジトリのインターフェース"""

    @abstractmethod
    async def get_by_id(self, db: AsyncSession, tag_id: uuid.UUID) -> Optional["Tag"]:
        """IDでタグを取得"""
        pass

    @abstractmethod
    async def get_by_user(self, db: AsyncSession, user_id: uuid.UUID, tag_id: uuid.UUID) -> Optional["Tag"]:
        """ユーザーIDとタグIDでタグを取得"""
        pass

    @abstractmethod
    async def get_user_tags(self, db: AsyncSession, user_id: uuid.UUID, skip: int = 0, limit: int = 20) -> list["Tag"]:
        """ユーザーのタグ一覧を取得"""
        pass


class TagRepository(TagRepositoryInterface):
    """タグリポジトリの実装"""

    async def get_by_id(self, db: AsyncSession, tag_id: uuid.UUID) -> Optional["Tag"]:
        """IDでタグを取得

        Args:
            db: データベースセッション
            tag_id: タグID

        Returns:
            タグインスタンスまたはNone
        """
        from app.crud.tag import tag_crud

        return await tag_crud.get(db, id=tag_id)

    async def get_by_user(self, db: AsyncSession, user_id: uuid.UUID, tag_id: uuid.UUID) -> Optional["Tag"]:
        """ユーザーIDとタグIDでタグを取得

        Args:
            db: データベースセッション
            user_id: ユーザーID
            tag_id: タグID

        Returns:
            タグインスタンスまたはNone
        """
        from app.crud.tag import tag_crud

        return await tag_crud.get_by_user(db, user_id=user_id, tag_id=tag_id)

    async def get_user_tags(self, db: AsyncSession, user_id: uuid.UUID, skip: int = 0, limit: int = 20) -> list["Tag"]:
        """ユーザーのタグ一覧を取得

        Args:
            db: データベースセッション
            user_id: ユーザーID
            skip: スキップ件数
            limit: 取得件数

        Returns:
            タグインスタンスのリスト
        """
        from app.crud.tag import tag_crud

        return await tag_crud.get_multi_by_user(db, user_id=user_id, skip=skip, limit=limit)

    async def get_with_task_counts(self, db: AsyncSession, tag_id: uuid.UUID, user_id: uuid.UUID) -> dict | None:
        """タスク数を含むタグデータを取得

        Args:
            db: データベースセッション
            tag_id: タグID
            user_id: ユーザーID

        Returns:
            TagResponse用の辞書データまたはNone
        """
        # タグをリレーションシップ込みで取得
        result = await db.execute(
            select(Tag).options(selectinload(Tag.task_tags)).where(Tag.id == tag_id, Tag.user_id == user_id)
        )
        tag = result.scalar_one_or_none()

        if not tag:
            return None

        tag_dict = {
            "id": tag.id,
            "user_id": tag.user_id,
            "name": tag.name,
            "color": tag.color,
            "description": tag.description,
            "is_active": tag.is_active,
            "created_at": tag.created_at,
            "updated_at": tag.updated_at,
            "task_count": tag.task_count,
            "active_task_count": tag.active_task_count,
            "completed_task_count": tag.completed_task_count,
            "color_rgb": tag.color_rgb,
            "is_preset_color": tag.is_preset_color,
        }

        return tag_dict

    async def create_with_response_data(self, tag: "Tag") -> dict:
        """タグ作成後にレスポンス用のデータを構築

        Args:
            tag: 作成されたタグインスタンス

        Returns:
            TagResponse用の辞書データ
        """
        # 基本データを取得
        tag_dict = {
            "id": tag.id,
            "user_id": tag.user_id,
            "name": tag.name,
            "color": tag.color,
            "description": tag.description,
            "is_active": tag.is_active,
            "created_at": tag.created_at,
            "updated_at": tag.updated_at,
            "task_count": 0,
            "active_task_count": 0,
            "completed_task_count": 0,
            "color_rgb": tag.color_rgb,
            "is_preset_color": tag.is_preset_color,
        }

        return tag_dict


# シングルトンインスタンス
tag_repository = TagRepository()
