"""セキュリティ・認証管理モジュール

JWT認証、Argon2パスワードハッシュ化、トークン管理を提供
"""

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
from app.core.database import get_db
from app.core.redis import cache

# 循環インポート回避のための型チェック時のみインポート
if TYPE_CHECKING:
    from app.models.user import User

# セキュリティ定数（Lint警告回避のため設定: 実際は問題ない）
TOKEN_TYPE_ACCESS = "access"  # nosec B105  # noqa: S105
TOKEN_TYPE_REFRESH = "refresh"  # nosec B105 # noqa: S105
TOKEN_TYPE_PASSWORD_RESET = "password_reset"  # nosec B105 # noqa: S105

# Argon2パスワードハッシャー（設定値を使用）
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
# current_user_dependency は get_current_user 定義後に設定


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
            import logging

            logger = logging.getLogger(__name__)
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
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

        # JTI（JWT ID）を追加してトークンを一意識別可能にする
        jti = str(uuid.uuid4())
        to_encode.update({"exp": expire, "iat": datetime.now(UTC), "jti": jti, "type": TOKEN_TYPE_ACCESS})

        try:
            encoded_jwt_raw = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
            # PyJWTのバージョンによってbytesまたはstrが返される可能性があるため変換
            encoded_jwt: str = (
                encoded_jwt_raw.decode("utf-8") if isinstance(encoded_jwt_raw, bytes) else encoded_jwt_raw
            )
            return encoded_jwt
        except Exception as e:
            raise RuntimeError(f"JWTトークン生成に失敗しました: {e}") from e

    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        """JWTリフレッシュトークン生成

        Args:
            user_id: ユーザーID

        Returns:
            JWT文字列
        """
        expire = datetime.now(UTC) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

        jti = str(uuid.uuid4())
        to_encode = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.now(UTC),
            "jti": jti,
            "type": TOKEN_TYPE_REFRESH,
        }

        try:
            encoded_jwt_raw = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
            # PyJWTのバージョンによってbytesまたはstrが返される可能性があるため変換
            encoded_jwt: str = (
                encoded_jwt_raw.decode("utf-8") if isinstance(encoded_jwt_raw, bytes) else encoded_jwt_raw
            )
            return encoded_jwt
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
            payload: dict[str, Any] = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

            # JTI（JWT ID）の確認
            jti = payload.get("jti")
            if not jti:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="無効なトークン形式です",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # トークンブラックリストのチェック
            is_blacklisted = await cache.exists(f"blacklist:{jti}")
            if is_blacklisted:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="トークンは無効化されています",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return payload

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
            # 予期しないエラー
            import logging

            logger = logging.getLogger(__name__)
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
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_exp": False},  # 期限切れトークンも処理
            )

            jti = payload.get("jti")
            exp = payload.get("exp")

            if jti and exp:
                # トークンの残り有効期限を計算
                current_time = datetime.now(UTC).timestamp()
                ttl = int(exp - current_time)

                # 有効期限がまだ残っている場合のみブラックリストに追加
                if ttl > 0:
                    await cache.set(f"blacklist:{jti}", "1", expire=ttl)

        except jwt.InvalidTokenError:
            # 無効なトークンは無視（既に無効なので問題なし）
            pass
        except Exception as e:
            # ブラックリスト登録の失敗はログに記録するが例外は発生させない
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"トークンブラックリスト登録に失敗: {e}")


# セキュリティマネージャーインスタンス
security_manager = SecurityManager()


async def get_current_user(
    db: AsyncSession = db_dependency, credentials: HTTPAuthorizationCredentials | None = security_dependency
) -> "User":
    """現在のユーザーを取得

    JWT認証を行い、有効なユーザーオブジェクトを返す

    Args:
        credentials: HTTPベアラー認証情報
        db: データベースセッション

    Returns:
        認証されたユーザーオブジェクト

    Raises:
        HTTPException: 認証に失敗した場合
    """
    # 認証情報の確認
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証が必要です",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # JWTトークン検証
    payload = await security_manager.verify_token(credentials.credentials)

    # ユーザーID取得（型安全性のためのチェック）
    user_id_raw = payload.get("sub")
    if user_id_raw is None or not isinstance(user_id_raw, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効な認証情報です",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id: str = user_id_raw

    # トークンタイプの確認
    token_type_raw = payload.get("type")
    if token_type_raw != TOKEN_TYPE_ACCESS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なトークンタイプです",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ユーザーの存在確認
    try:
        # 循環インポートを避けるため、ここでインポート
        from app.crud.user import user_crud

        user = await user_crud.get(db, id=uuid.UUID(user_id))
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ユーザーが見つかりません",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except ValueError:
        # UUID変換エラー
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なユーザーIDです",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except ImportError:
        # CRUDモジュールが未実装の場合
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="認証システムが正しく設定されていません",
        ) from None

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


# セキュリティユーティリティ関数
def generate_password_reset_token(user_id: str) -> str:
    """パスワードリセットトークン生成

    Args:
        user_id: ユーザーID

    Returns:
        パスワードリセット用JWT
    """
    expire = datetime.now(UTC) + timedelta(hours=1)  # 1時間有効

    to_encode = {"sub": user_id, "exp": expire, "iat": datetime.now(UTC), "type": TOKEN_TYPE_PASSWORD_RESET}

    encoded_jwt_raw = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    # PyJWTのバージョンによってbytesまたはstrが返される可能性があるため変換
    encoded_jwt: str = encoded_jwt_raw.decode("utf-8") if isinstance(encoded_jwt_raw, bytes) else encoded_jwt_raw
    return encoded_jwt


def verify_password_reset_token(token: str) -> str | None:
    """パスワードリセットトークン検証

    Args:
        token: パスワードリセットトークン

    Returns:
        有効な場合はユーザーID、無効な場合はNone
    """
    try:
        payload: dict[str, Any] = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        if payload.get("type") != TOKEN_TYPE_PASSWORD_RESET:
            return None

        # 型安全性のためのチェック
        user_id_raw = payload.get("sub")
        if user_id_raw is None or not isinstance(user_id_raw, str):
            return None

        # 型を明示的にキャスト
        user_id: str = user_id_raw
        return user_id

    except jwt.InvalidTokenError:
        return None
