"""認証サービス

認証に関するビジネスロジックを提供
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import security_manager
from app.crud.user import user_crud
from app.models.user import User
from app.schemas.auth import UserCreate


class AuthService:
    """認証サービスクラス

    ユーザー認証、登録、パスワード管理のビジネスロジックを提供
    """

    async def authenticate_user(self, db: AsyncSession, email: str, password: str) -> User | None:
        """ユーザー認証

        Args:
            db: データベースセッション
            email: メールアドレス
            password: パスワード

        Returns:
            認証成功時はユーザーオブジェクト、失敗時はNone
        """
        # メールアドレスでユーザー検索
        user = await user_crud.get_by_email(db, email=email)
        if not user:
            return None

        # アカウント状態チェック
        if not user.can_login:
            return None

        # パスワード検証
        if not security_manager.verify_password(password, user.password_hash):
            # ログイン失敗を記録
            await user_crud.update_login_failure(db, user=user)
            return None

        # パスワード再ハッシュが必要かチェック
        if security_manager.needs_rehash(user.password_hash):
            new_hash = security_manager.get_password_hash(password)
            await user_crud.update_password(db, user=user, password_hash=new_hash)

        # ログイン成功を記録
        await user_crud.update_last_login(db, user=user)

        return user

    async def create_user(self, db: AsyncSession, user_in: UserCreate) -> User:
        """新規ユーザー作成

        Args:
            db: データベースセッション
            user_in: ユーザー作成データ

        Returns:
            作成されたユーザーオブジェクト

        Raises:
            ValueError: メールアドレスが既に使用されている場合
            RuntimeError: ユーザー作成に失敗した場合
        """
        # メールアドレス重複チェック
        if await user_crud.is_email_taken(db, email=user_in.email):
            raise ValueError("このメールアドレスは既に登録されています")

        # パスワードハッシュ化
        password_hash = security_manager.get_password_hash(user_in.password)

        # ユーザー作成
        try:
            user = await user_crud.create_user(db, obj_in=user_in, password_hash=password_hash)
            return user
        except Exception as e:
            raise RuntimeError(f"ユーザー作成に失敗しました: {e}") from e

    async def change_password(self, db: AsyncSession, user: User, current_password: str, new_password: str) -> bool:
        """パスワード変更

        Args:
            db: データベースセッション
            user: 対象ユーザー
            current_password: 現在のパスワード
            new_password: 新しいパスワード

        Returns:
            変更成功時はTrue、失敗時はFalse

        Raises:
            ValueError: 現在のパスワードが正しくない場合
            RuntimeError: パスワード更新に失敗した場合
        """
        # 現在のパスワード確認
        if not security_manager.verify_password(current_password, user.password_hash):
            raise ValueError("現在のパスワードが正しくありません")

        # 新しいパスワードのハッシュ化
        new_password_hash = security_manager.get_password_hash(new_password)

        # パスワード更新
        try:
            await user_crud.update_password(db, user=user, password_hash=new_password_hash)
            return True
        except Exception as e:
            raise RuntimeError(f"パスワード更新に失敗しました: {e}") from e

    async def reset_password(self, db: AsyncSession, email: str, new_password: str, reset_token: str) -> bool:
        """パスワードリセット

        Args:
            db: データベースセッション
            email: メールアドレス
            new_password: 新しいパスワード
            reset_token: リセットトークン

        Returns:
            リセット成功時はTrue、失敗時はFalse

        Raises:
            ValueError: トークンが無効またはユーザーが見つからない場合
            RuntimeError: パスワード更新に失敗した場合
        """
        # トークン検証
        from app.core.security import verify_password_reset_token

        user_id = verify_password_reset_token(reset_token)
        if not user_id:
            raise ValueError("無効なリセットトークンです")

        # ユーザー取得
        user = await user_crud.get(db, id=user_id)
        if not user or user.email != email.lower().strip():
            raise ValueError("ユーザーが見つかりません")

        # 新しいパスワードのハッシュ化
        new_password_hash = security_manager.get_password_hash(new_password)

        # パスワード更新とロック解除
        try:
            await user_crud.update_password(db, user=user, password_hash=new_password_hash)
            if user.is_locked:
                await user_crud.unlock_user(db, user=user)
            return True
        except Exception as e:
            raise RuntimeError(f"パスワードリセットに失敗しました: {e}") from e

    async def generate_password_reset_token(self, db: AsyncSession, email: str) -> str | None:
        """パスワードリセットトークン生成

        Args:
            db: データベースセッション
            email: メールアドレス

        Returns:
            ユーザーが存在する場合はリセットトークン、しない場合はNone
        """
        # ユーザー存在確認
        user = await user_crud.get_by_email(db, email=email)
        if not user or not user.is_active:
            return None

        # リセットトークン生成
        from app.core.security import generate_password_reset_token

        return generate_password_reset_token(str(user.id))

    async def verify_user_email(self, db: AsyncSession, user: User) -> User:
        """メールアドレス認証

        Args:
            db: データベースセッション
            user: 認証対象のユーザー

        Returns:
            更新されたユーザーオブジェクト
        """
        return await user_crud.verify_email(db, user=user)

    async def deactivate_user(self, db: AsyncSession, user: User) -> User:
        """ユーザー無効化

        Args:
            db: データベースセッション
            user: 無効化対象のユーザー

        Returns:
            更新されたユーザーオブジェクト
        """
        return await user_crud.deactivate_user(db, user=user)

    async def unlock_user_account(self, db: AsyncSession, user_id: str) -> User | None:
        """ユーザーアカウントロック解除（管理者用）

        Args:
            db: データベースセッション
            user_id: ユーザーID

        Returns:
            解除されたユーザーオブジェクト、見つからない場合はNone
        """
        user = await user_crud.get(db, id=user_id)
        if not user:
            return None

        return await user_crud.unlock_user(db, user=user)


auth_service = AuthService()
