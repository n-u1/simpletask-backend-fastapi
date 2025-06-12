"""ユーザーCRUD操作

ユーザーモデルに特化したCRUD操作を提供
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.auth import UserCreate
from app.schemas.user import UserUpdate
from app.utils.error_handler import handle_db_operation


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """ユーザーCRUDクラス

    ユーザーモデル専用のCRUD操作を提供
    認証、基本管理機能を含む
    """

    @handle_db_operation("メールアドレスでのユーザー取得")
    async def get_by_email(self, db: AsyncSession, *, email: str) -> User | None:
        """メールアドレスでユーザーを取得

        Args:
            db: データベースセッション
            email: メールアドレス

        Returns:
            見つかった場合はユーザーインスタンス、見つからない場合はNone
        """
        stmt = select(self.model).where(self.model.email == email.lower().strip())
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @handle_db_operation("ユーザー作成")
    async def create_user(self, db: AsyncSession, *, obj_in: UserCreate, password_hash: str) -> User:
        """ユーザー作成

        Args:
            db: データベースセッション
            obj_in: ユーザー作成データ
            password_hash: ハッシュ化済みパスワード

        Returns:
            作成されたユーザーインスタンス

        Raises:
            Exception: データベースエラーの場合
        """
        # ユーザーデータの準備
        user_data = {
            "email": obj_in.email.lower().strip(),
            "password_hash": password_hash,
            "display_name": obj_in.display_name.strip(),
            "is_active": True,
            "is_verified": False,  # メール認証は別途実装
        }

        # ユーザー作成
        db_user = self.model(**user_data)
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user

    @handle_db_operation("パスワード更新")
    async def update_password(self, db: AsyncSession, *, user: User, password_hash: str) -> User:
        """ユーザーのパスワードを更新

        Args:
            db: データベースセッション
            user: 更新対象のユーザー
            password_hash: 新しいハッシュ化済みパスワード

        Returns:
            更新されたユーザーインスタンス

        Raises:
            Exception: データベースエラーの場合
        """
        user.password_hash = password_hash
        await db.commit()
        await db.refresh(user)
        return user

    @handle_db_operation("最終ログイン時刻更新")
    async def update_last_login(self, db: AsyncSession, *, user: User) -> User:
        """最終ログイン時刻を更新

        Args:
            db: データベースセッション
            user: 更新対象のユーザー

        Returns:
            更新されたユーザーインスタンス
        """
        user.record_login_success()
        await db.commit()
        await db.refresh(user)
        return user


user_crud = CRUDUser(User)
