"""タグリポジトリ

タグデータアクセス層の抽象化
"""

import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
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


# シングルトンインスタンス
tag_repository = TagRepository()
