"""認証サービス

ユーザー認証とアカウント管理のビジネスロジックを提供
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import security_manager
from app.crud.user import user_crud
from app.models.user import User
from app.schemas.auth import UserCreate


class AuthService:
    async def authenticate_user(self, db: AsyncSession, email: str, password: str) -> User | None:
        """ユーザー認証"""
        # メールアドレスでユーザー検索
        user = await user_crud.get_by_email(db, email=email)
        if not user:
            return None

        # パスワード検証
        if not security_manager.verify_password(password, user.password_hash):
            return None

        # アクティブユーザーチェック
        if not user.can_login:
            return None

        return user

    async def create_user(self, db: AsyncSession, user_in: UserCreate) -> User:
        """新規ユーザー作成"""
        # メールアドレス重複チェック
        existing_user = await user_crud.get_by_email(db, email=user_in.email)
        if existing_user:
            raise ValueError("このメールアドレスは既に使用されています")

        # パスワードハッシュ化
        hashed_password = security_manager.get_password_hash(user_in.password)

        # ユーザー作成データ準備
        user_data = {
            "email": user_in.email,
            "password_hash": hashed_password,
            "display_name": user_in.display_name,
            "is_active": True,
        }

        return await user_crud.create(db, obj_in=user_data)


auth_service = AuthService()
