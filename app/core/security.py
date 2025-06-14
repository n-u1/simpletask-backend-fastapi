"""セキュリティ・認証管理モジュール

JWT認証、Argon2パスワードハッシュ化、トークン管理を提供
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import (
    HashingError,
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import ErrorMessages
from app.core.database import get_db
from app.core.redis import cache
from app.utils.jwt_helpers import (
    TOKEN_TYPE_ACCESS,
    create_jwt_helper,
    extract_jti_from_token,
    extract_user_id_from_token,
    validate_token_type,
)

# 循環インポート回避のための型チェック時
if TYPE_CHECKING:
    from app.models.user import User

logger = logging.getLogger(__name__)

jwt_helper = create_jwt_helper(settings.JWT_SECRET_KEY, settings.JWT_ALGORITHM)

argon2_config = settings.get_argon2_config()
pwd_hasher = PasswordHasher(
    time_cost=argon2_config["time_cost"],
    memory_cost=argon2_config["memory_cost"],
    parallelism=argon2_config["parallelism"],
    hash_len=argon2_config["hash_len"],
    salt_len=argon2_config["salt_len"],
)

# JWT Bearer認証
security = HTTPBearer(auto_error=False)

# モジュールレベルの依存関数（Lint警告回避のため設定）
security_dependency = Depends(security)
db_dependency = Depends(get_db)


class SecurityManager:
    """セキュリティ管理クラス

    JWT認証、パスワードハッシュ化、トークン管理を統括
    """

    @staticmethod
    def verify_password(plain_password: str, password_hash: str) -> bool:
        """パスワード検証

        Args:
            plain_password: 平文パスワード
            password_hash: Argon2ハッシュ

        Returns:
            パスワードが一致する場合True
        """
        try:
            pwd_hasher.verify(password_hash, plain_password)
            return True
        except (VerificationError, VerifyMismatchError, InvalidHashError):
            return False
        except Exception as e:
            # 予期しないエラーをログに記録（本番環境では詳細ログ）
            logger.error(f"パスワード検証中に予期しないエラー: {e}")
            return False

    @staticmethod
    def get_password_hash(password: str) -> str:
        """パスワードをArgon2でハッシュ化

        Args:
            password: 平文パスワード

        Returns:
            Argon2ハッシュ文字列

        Raises:
            ValueError: パスワードが空または無効な場合
            RuntimeError: ハッシュ化に失敗した場合
        """
        if not password or not password.strip():
            raise ValueError("パスワードが空です")

        try:
            hash_result: str = pwd_hasher.hash(password)
            return hash_result
        except HashingError as e:
            raise RuntimeError(f"パスワードハッシュ化に失敗しました: {e}") from e

    @staticmethod
    def needs_rehash(password_hash: str) -> bool:
        """パスワードハッシュの再ハッシュが必要かチェック

        Argon2パラメータが変更された場合に既存ハッシュの更新が必要

        Args:
            password_hash: 既存のパスワードハッシュ

        Returns:
            再ハッシュが必要な場合True
        """
        try:
            needs_rehash_result: bool = pwd_hasher.check_needs_rehash(password_hash)
            return needs_rehash_result
        except Exception:
            # 無効なハッシュの場合は再ハッシュが必要
            return True

    @staticmethod
    def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
        """JWTアクセストークン生成

        Args:
            data: トークンに含めるデータ
            expires_delta: 有効期限（未指定時は設定値を使用）

        Returns:
            JWT文字列

        Raises:
            ValueError: ユーザーIDが指定されていない場合
            RuntimeError: トークン生成に失敗した場合
        """
        user_id = data.get("sub")
        if not user_id:
            raise ValueError("ユーザーIDが指定されていません")

        if expires_delta is None:
            expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

        # 追加クレームの抽出（sub以外）
        additional_claims = {k: v for k, v in data.items() if k != "sub"}

        try:
            return jwt_helper.create_access_token(
                user_id=str(user_id),
                expires_delta=expires_delta,
                additional_claims=additional_claims if additional_claims else None,
            )
        except Exception as e:
            raise RuntimeError(f"JWTトークン生成に失敗しました: {e}") from e

    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        """JWTリフレッシュトークン生成

        Args:
            user_id: ユーザーID

        Returns:
            JWT文字列

        Raises:
            RuntimeError: トークン生成に失敗した場合
        """
        expires_delta = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

        try:
            return jwt_helper.create_refresh_token(user_id, expires_delta)
        except Exception as e:
            raise RuntimeError(f"リフレッシュトークン生成に失敗しました: {e}") from e

    @staticmethod
    async def verify_token(token: str) -> dict[str, Any]:
        """JWTトークン検証

        Args:
            token: JWT文字列

        Returns:
            デコードされたペイロード

        Raises:
            HTTPException: トークンが無効な場合
        """
        try:
            payload = jwt_helper.decode(token)

            # JTI（JWT ID）の確認
            jti = extract_jti_from_token(payload)

            # トークンブラックリストのチェック
            is_blacklisted = await cache.exists(f"blacklist:{jti}")
            if is_blacklisted:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="トークンは無効化されています",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return payload

        except ValueError as e:
            # extract_jti_from_token からのエラー
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            ) from e
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="トークンの有効期限が切れています",
                headers={"WWW-Authenticate": "Bearer"},
            ) from None
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無効なトークンです",
                headers={"WWW-Authenticate": "Bearer"},
            ) from None
        except Exception as e:
            logger.error(f"トークン検証中に予期しないエラー: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="認証に失敗しました",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

    @staticmethod
    async def blacklist_token(token: str) -> None:
        """トークンをブラックリストに追加

        ログアウト時やセキュリティ上の理由でトークンを無効化

        Args:
            token: 無効化するJWT文字列
        """
        try:
            # JTI抽出（期限切れトークンも処理）
            jti = jwt_helper.extract_jti(token)

            # トークンペイロードから有効期限取得
            payload = jwt_helper.decode(token, verify_exp=False)
            exp = payload.get("exp")

            if exp:
                current_time = datetime.now(UTC).timestamp()
                ttl = int(exp - current_time)

                # 有効期限がまだ残っている場合のみブラックリストに追加
                if ttl > 0:
                    await cache.set(f"blacklist:{jti}", "1", expire=ttl)

        except Exception as e:
            # ブラックリスト登録の失敗はログに記録するが例外は発生させない
            logger.warning(f"トークンブラックリスト登録に失敗: {e}")


security_manager = SecurityManager()


async def get_current_user(
    db: AsyncSession = db_dependency, credentials: HTTPAuthorizationCredentials | None = security_dependency
) -> "User":
    """現在のユーザーを取得

    JWT認証を行い、有効なユーザーオブジェクトを返す
    認証に必要な機密情報アクセスのためSQLAlchemyモデルを返す

    Args:
        credentials: HTTPベアラー認証情報
        db: データベースセッション

    Returns:
        認証されたユーザーオブジェクト（SQLAlchemy）

    Raises:
        HTTPException: 認証に失敗した場合
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorMessages.UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )

    # JWTトークン検証
    payload = await security_manager.verify_token(credentials.credentials)

    # ユーザーID取得（型安全性のためのチェック）
    try:
        user_id = extract_user_id_from_token(payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    # トークンタイプの確認
    if not validate_token_type(payload, TOKEN_TYPE_ACCESS):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なトークンタイプです",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ユーザーの存在確認（認証用なので機密情報込みで取得）
    try:
        from app.repositories.user import user_repository

        user_dto = await user_repository.get_by_id(db, uuid.UUID(user_id))

        if user_dto is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorMessages.USER_NOT_FOUND,
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 認証処理のため、SQLAlchemyモデルを取得し直す
        # （パスワード更新などで必要）
        from app.crud.user import user_crud

        user = await user_crud.get(db, id=uuid.UUID(user_id))

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorMessages.USER_NOT_FOUND,
                headers={"WWW-Authenticate": "Bearer"},
            )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なユーザーIDです",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except Exception as e:
        logger.error(f"ユーザー取得中にエラーが発生しました: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="認証システムが正しく設定されていません",
        ) from e

    # アクティブユーザーの確認
    if not user.can_login:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="アカウントが無効またはロックされています",
        )

    return user


# get_current_user 定義後に依存関数を設定
current_user_dependency = Depends(get_current_user)


async def get_current_active_user(current_user: "User" = current_user_dependency) -> "User":
    """現在のアクティブユーザーを取得

    get_current_userの追加チェック版（互換性のため）

    Args:
        current_user: 認証済みユーザー

    Returns:
        アクティブなユーザーオブジェクト

    Raises:
        HTTPException: ユーザーが非アクティブな場合
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="アカウントが無効です",
        )
    return current_user


async def get_current_user_optional(
    db: AsyncSession = db_dependency, credentials: HTTPAuthorizationCredentials | None = security_dependency
) -> Optional["User"]:
    """オプション認証

    認証情報がない場合はNoneを返し、エラーにしない
    パブリック・プライベート両対応のエンドポイントで使用

    Args:
        credentials: HTTPベアラー認証情報
        db: データベースセッション

    Returns:
        認証されたユーザーオブジェクトまたはNone
    """
    if not credentials:
        return None

    try:
        return await get_current_user(db=db, credentials=credentials)
    except HTTPException:
        # 認証エラーの場合はNoneを返す
        return None


def generate_password_reset_token(user_id: str) -> str:
    """パスワードリセットトークン生成

    Args:
        user_id: ユーザーID

    Returns:
        パスワードリセット用JWT

    Raises:
        RuntimeError: トークン生成に失敗した場合
    """
    expires_delta = timedelta(hours=1)

    try:
        return jwt_helper.create_password_reset_token(user_id, expires_delta)
    except Exception as e:
        raise RuntimeError(f"パスワードリセットトークン生成に失敗しました: {e}") from e


def verify_password_reset_token(token: str) -> str | None:
    """パスワードリセットトークン検証

    Args:
        token: パスワードリセットトークン

    Returns:
        有効な場合はユーザーID、無効な場合はNone
    """
    try:
        return jwt_helper.verify_password_reset_token(token)
    except Exception:
        return None
