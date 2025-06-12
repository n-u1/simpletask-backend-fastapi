"""認証サービス

ユーザー認証とアカウント管理のビジネスロジックを提供
"""

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import security_manager
from app.crud.user import user_crud
from app.schemas.auth import UserCreate
from app.utils.error_handler import handle_service_error

# 循環インポート回避のための型チェック時
if TYPE_CHECKING:
    from app.models.user import User


class AuthService:
    @handle_service_error("ユーザー認証")
    async def authenticate_user(self, db: AsyncSession, email: str, password: str) -> "User | None":
        """ユーザー認証"""
        # メールアドレスでユーザー検索
        user: User | None = await user_crud.get_by_email(db, email=email)
        if not user:
            return None

        # パスワード検証
        if not security_manager.verify_password(password, user.password_hash):
            return None

        # アクティブユーザーチェック
        if not user.can_login:
            return None

        return user

    @handle_service_error("ユーザー作成")
    async def create_user(self, db: AsyncSession, user_in: UserCreate) -> "User":
        """新規ユーザー作成"""
        # メールアドレス重複チェック
        existing_user: User | None = await user_crud.get_by_email(db, email=user_in.email)
        if existing_user:
            raise ValueError("このメールアドレスは既に使用されています")

        # パスワードハッシュ化
        hashed_password: str = security_manager.get_password_hash(user_in.password)

        # ユーザー作成データ準備
        user_data = {
            "email": user_in.email,
            "password_hash": hashed_password,
            "display_name": user_in.display_name,
            "is_active": True,
        }

        created_user: User = await user_crud.create(db, obj_in=user_data)
        return created_user


auth_service = AuthService()
