"""ユーザーリポジトリ

ユーザーデータアクセス層の抽象化
CRUDOperationsをカプセル化し、ビジネスロジックから分離
"""

import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.models.user import User


class UserRepositoryInterface(ABC):
    """ユーザーリポジトリのインターフェース"""

    @abstractmethod
    async def get_by_id(self, db: AsyncSession, user_id: uuid.UUID) -> Optional["User"]:
        """IDでユーザーを取得"""
        pass

    @abstractmethod
    async def get_by_email(self, db: AsyncSession, email: str) -> Optional["User"]:
        """メールアドレスでユーザーを取得"""
        pass

    @abstractmethod
    async def create(self, db: AsyncSession, email: str, password_hash: str, display_name: str) -> "User":
        """ユーザーを作成"""
        pass

    @abstractmethod
    async def update_password(self, db: AsyncSession, user: "User", password_hash: str) -> "User":
        """パスワードを更新"""
        pass

    @abstractmethod
    async def update_last_login(self, db: AsyncSession, user: "User") -> "User":
        """最終ログイン時刻を更新"""
        pass


class UserRepository(UserRepositoryInterface):
    """ユーザーリポジトリの実装

    CRUD操作をカプセル化し、ドメインロジックに適した形でデータアクセスを提供
    """

    async def get_by_id(self, db: AsyncSession, user_id: uuid.UUID) -> Optional["User"]:
        """IDでユーザーを取得

        Args:
            db: データベースセッション
            user_id: ユーザーID

        Returns:
            ユーザーインスタンスまたはNone
        """
        from app.crud.user import user_crud

        return await user_crud.get(db, id=user_id)

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional["User"]:
        """メールアドレスでユーザーを取得

        Args:
            db: データベースセッション
            email: メールアドレス

        Returns:
            ユーザーインスタンスまたはNone
        """
        from app.crud.user import user_crud

        return await user_crud.get_by_email(db, email=email)

    async def create(self, db: AsyncSession, email: str, password_hash: str, display_name: str) -> "User":
        """ユーザーを作成

        Args:
            db: データベースセッション
            email: メールアドレス
            password_hash: ハッシュ化済みパスワード
            display_name: 表示名

        Returns:
            作成されたユーザーインスタンス
        """
        from app.crud.user import user_crud
        from app.schemas.auth import UserCreate

        user_create = UserCreate(
            email=email,
            password="dummy",  # nosec B106  # noqa: S106 # 実際のパスワードは別途ハッシュ化済み
            display_name=display_name,
        )

        return await user_crud.create_user(db, obj_in=user_create, password_hash=password_hash)

    async def update_password(self, db: AsyncSession, user: "User", password_hash: str) -> "User":
        """パスワードを更新

        Args:
            db: データベースセッション
            user: 更新対象のユーザー
            password_hash: 新しいハッシュ化済みパスワード

        Returns:
            更新されたユーザーインスタンス
        """
        from app.crud.user import user_crud

        return await user_crud.update_password(db, user=user, password_hash=password_hash)

    async def update_last_login(self, db: AsyncSession, user: "User") -> "User":
        """最終ログイン時刻を更新

        Args:
            db: データベースセッション
            user: 更新対象のユーザー

        Returns:
            更新されたユーザーインスタンス
        """
        from app.crud.user import user_crud

        return await user_crud.update_last_login(db, user=user)


# シングルトンインスタンス
user_repository = UserRepository()
