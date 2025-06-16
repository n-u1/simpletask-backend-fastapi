"""ユーザーリポジトリ

ユーザーデータアクセス層の抽象化
"""

import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import UserResponse, UserSummary

if TYPE_CHECKING:
    from app.models.user import User
else:
    from app.models.user import User


class UserRepositoryInterface(ABC):
    """ユーザーリポジトリのインターフェース"""

    @abstractmethod
    async def get_by_id(self, db: AsyncSession, user_id: uuid.UUID) -> UserResponse | None:
        """IDでユーザーを取得"""
        pass

    @abstractmethod
    async def get_by_email(self, db: AsyncSession, email: str) -> UserResponse | None:
        """メールアドレスでユーザーを取得"""
        pass

    @abstractmethod
    async def get_summary_by_id(self, db: AsyncSession, user_id: uuid.UUID) -> UserSummary | None:
        """IDでユーザー要約情報を取得"""
        pass

    @abstractmethod
    async def get_with_auth_info(self, db: AsyncSession, email: str) -> "User | None":
        """認証情報込みでユーザーを取得（認証専用）"""
        pass

    @abstractmethod
    async def update_password(self, db: AsyncSession, user: "User", password_hash: str) -> "User":
        """ユーザーのパスワードを更新"""
        pass


class UserRepository(UserRepositoryInterface):
    """ユーザーリポジトリの実装"""

    async def get_by_id(self, db: AsyncSession, user_id: uuid.UUID) -> UserResponse | None:
        """IDでユーザーを取得"""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return None

        # Pydanticレスポンスモデルに変換（機密情報は除外）
        user_data: dict[str, Any] = {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "last_login_at": user.last_login_at,
            "locked_until": user.locked_until,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }

        return UserResponse.model_validate(user_data)

    async def get_by_email(self, db: AsyncSession, email: str) -> UserResponse | None:
        """メールアドレスでユーザーを取得

        認証時などで使用
        """
        stmt = select(User).where(User.email == email.lower().strip())
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return None

        # Pydanticレスポンスモデルに変換（セッション内）
        user_data: dict[str, Any] = {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "last_login_at": user.last_login_at,
            "locked_until": user.locked_until,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }

        return UserResponse.model_validate(user_data)

    async def get_summary_by_id(self, db: AsyncSession, user_id: uuid.UUID) -> UserSummary | None:
        """IDでユーザー要約情報を取得

        他の機能でユーザー情報を参照する際に使用する軽量版
        """
        stmt = select(User.id, User.display_name, User.avatar_url).where(
            User.id == user_id,
            User.is_active == True,  # noqa: E712
        )
        result = await db.execute(stmt)
        row = result.first()

        if not row:
            return None

        return UserSummary(
            id=row.id,
            display_name=row.display_name,
            avatar_url=row.avatar_url,
        )

    async def get_with_auth_info(self, db: AsyncSession, email: str) -> User | None:
        """認証情報込みでユーザーを取得（認証専用）

        認証時にパスワードハッシュなどが必要な場合のみ使用
        SQLAlchemyモデルを直接返す（機密情報アクセスのため）
        """
        stmt = select(User).where(User.email == email.lower().strip())
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_password(self, db: AsyncSession, user: User, password_hash: str) -> User:
        """ユーザーのパスワードを更新

        Args:
            db: データベースセッション
            user: 更新対象のユーザー（SQLAlchemyモデル）
            password_hash: 新しいハッシュ化済みパスワード

        Returns:
            更新されたユーザー（SQLAlchemyモデル）
        """
        user.password_hash = password_hash
        await db.commit()
        await db.refresh(user)
        return user


# シングルトンインスタンス
user_repository = UserRepository()
