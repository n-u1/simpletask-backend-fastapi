"""ユーザーCRUD操作

ユーザーモデルに特化したCRUD操作を提供
"""

from typing import TYPE_CHECKING

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from collections.abc import Sequence

from datetime import UTC

from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.auth import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """ユーザーCRUDクラス

    ユーザーモデル専用のCRUD操作を提供
    認証、検索、状態管理などの機能を含む
    """

    async def get_by_email(self, db: AsyncSession, *, email: str) -> User | None:
        """メールアドレスでユーザーを取得

        Args:
            db: データベースセッション
            email: メールアドレス

        Returns:
            見つかった場合はユーザーインスタンス、見つからない場合はNone
        """
        try:
            stmt = select(User).where(User.email == email.lower().strip())
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"メールアドレスでのユーザー取得エラー ({email}): {e}")
            return None

    async def get_active_users(self, db: AsyncSession, *, skip: int = 0, limit: int = 100) -> list[User]:
        """アクティブなユーザー一覧を取得

        Args:
            db: データベースセッション
            skip: スキップする件数
            limit: 取得する最大件数

        Returns:
            アクティブなユーザーのリスト
        """
        try:
            stmt = (
                select(User)
                .where(User.is_active)  # True との比較を避ける
                .order_by(User.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await db.execute(stmt)
            users: Sequence[User] = result.scalars().all()
            return list(users)

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"アクティブユーザー一覧取得エラー: {e}")
            return []

    async def search_users(
        self, db: AsyncSession, *, query: str, skip: int = 0, limit: int = 100, active_only: bool = True
    ) -> list[User]:
        """ユーザー検索

        表示名またはメールアドレスで部分一致検索

        Args:
            db: データベースセッション
            query: 検索クエリ
            skip: スキップする件数
            limit: 取得する最大件数
            active_only: アクティブユーザーのみ検索するか

        Returns:
            検索にマッチしたユーザーのリスト
        """
        try:
            search_term = f"%{query.strip()}%"

            stmt = select(User).where(or_(User.display_name.ilike(search_term), User.email.ilike(search_term)))

            if active_only:
                stmt = stmt.where(User.is_active)  # True との比較を避ける

            stmt = stmt.order_by(User.display_name).offset(skip).limit(limit)

            result = await db.execute(stmt)
            users: Sequence[User] = result.scalars().all()
            return list(users)
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"ユーザー検索エラー (query: {query}): {e}")
            return []

    async def create_user(self, db: AsyncSession, *, obj_in: UserCreate, password_hash: str) -> User:
        """ユーザー作成（パスワードハッシュ付き）

        Args:
            db: データベースセッション
            obj_in: ユーザー作成データ
            password_hash: ハッシュ化済みパスワード

        Returns:
            作成されたユーザーインスタンス

        Raises:
            Exception: データベースエラーの場合
        """
        try:
            # ユーザーデータの準備
            user_data = {
                "email": obj_in.email.lower().strip(),
                "password_hash": password_hash,
                "display_name": obj_in.display_name.strip(),
                "is_active": True,
                "is_verified": False,  # メール認証は別途実装
            }

            # ユーザー作成
            db_user = User(**user_data)
            db.add(db_user)
            await db.commit()
            await db.refresh(db_user)
            return db_user

        except Exception as e:
            await db.rollback()
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"ユーザー作成エラー: {e}")
            raise

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
        try:
            user.password_hash = password_hash
            await db.commit()
            await db.refresh(user)
            return user
        except Exception as e:
            await db.rollback()
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"パスワード更新エラー (user_id: {user.id}): {e}")
            raise

    async def update_last_login(self, db: AsyncSession, *, user: User) -> User:
        """最終ログイン時刻を更新

        Args:
            db: データベースセッション
            user: 更新対象のユーザー

        Returns:
            更新されたユーザーインスタンス
        """
        try:
            user.record_login_success()
            await db.commit()
            await db.refresh(user)
            return user
        except Exception as e:
            await db.rollback()
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"最終ログイン時刻更新エラー (user_id: {user.id}): {e}")
            raise

    async def update_login_failure(
        self, db: AsyncSession, *, user: User, max_attempts: int = 5, lockout_duration_minutes: int = 30
    ) -> User:
        """ログイン失敗を記録

        Args:
            db: データベースセッション
            user: 更新対象のユーザー
            max_attempts: 最大失敗回数
            lockout_duration_minutes: ロック時間（分）

        Returns:
            更新されたユーザーインスタンス
        """
        try:
            user.record_login_failure(max_attempts, lockout_duration_minutes)
            await db.commit()
            await db.refresh(user)
            return user
        except Exception as e:
            await db.rollback()
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"ログイン失敗記録エラー (user_id: {user.id}): {e}")
            raise

    async def activate_user(self, db: AsyncSession, *, user: User) -> User:
        """ユーザーをアクティブ化

        Args:
            db: データベースセッション
            user: アクティブ化対象のユーザー

        Returns:
            更新されたユーザーインスタンス
        """
        try:
            user.is_active = True
            await db.commit()
            await db.refresh(user)
            return user
        except Exception as e:
            await db.rollback()
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"ユーザーアクティブ化エラー (user_id: {user.id}): {e}")
            raise

    async def deactivate_user(self, db: AsyncSession, *, user: User) -> User:
        """ユーザーを非アクティブ化

        Args:
            db: データベースセッション
            user: 非アクティブ化対象のユーザー

        Returns:
            更新されたユーザーインスタンス
        """
        try:
            user.is_active = False
            await db.commit()
            await db.refresh(user)
            return user
        except Exception as e:
            await db.rollback()
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"ユーザー非アクティブ化エラー (user_id: {user.id}): {e}")
            raise

    async def verify_email(self, db: AsyncSession, *, user: User) -> User:
        """メールアドレスを認証済みにする

        Args:
            db: データベースセッション
            user: 認証対象のユーザー

        Returns:
            更新されたユーザーインスタンス
        """
        try:
            user.is_verified = True
            await db.commit()
            await db.refresh(user)
            return user
        except Exception as e:
            await db.rollback()
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"メール認証エラー (user_id: {user.id}): {e}")
            raise

    async def get_locked_users(self, db: AsyncSession) -> list[User]:
        """ロックされているユーザー一覧を取得

        Args:
            db: データベースセッション

        Returns:
            ロックされているユーザーのリスト
        """
        try:
            from datetime import datetime

            current_time = datetime.now(UTC)

            stmt = (
                select(User)
                .where(and_(User.locked_until.is_not(None), User.locked_until > current_time))
                .order_by(User.locked_until.desc())
            )

            result = await db.execute(stmt)
            users: Sequence[User] = result.scalars().all()
            return list(users)

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"ロックユーザー一覧取得エラー: {e}")
            return []

    async def unlock_user(self, db: AsyncSession, *, user: User) -> User:
        """ユーザーのロックを解除

        Args:
            db: データベースセッション
            user: ロック解除対象のユーザー

        Returns:
            更新されたユーザーインスタンス
        """
        try:
            user.failed_login_attempts = 0
            user.locked_until = None
            await db.commit()
            await db.refresh(user)
            return user
        except Exception as e:
            await db.rollback()
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"ユーザーロック解除エラー (user_id: {user.id}): {e}")
            raise

    async def is_email_taken(self, db: AsyncSession, *, email: str) -> bool:
        """メールアドレスが既に使用されているかチェック

        Args:
            db: データベースセッション
            email: チェック対象のメールアドレス

        Returns:
            使用済みの場合True、未使用の場合False
        """
        try:
            stmt = select(User.id).where(User.email == email.lower().strip())
            result = await db.execute(stmt)
            return result.scalar_one_or_none() is not None
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"メールアドレス重複チェックエラー ({email}): {e}")
            return True


# CRUDインスタンス
user_crud = CRUDUser(User)
