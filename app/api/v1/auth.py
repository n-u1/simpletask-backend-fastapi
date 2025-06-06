"""認証APIエンドポイント

ユーザー登録、ログイン、トークン管理のAPIを提供
"""

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import rate_limiter
from app.core.security import get_current_user, security_manager
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    PasswordChangeRequest,
    RefreshTokenRequest,
    Token,
    UserCreate,
    UserResponse,
)
from app.services.auth import auth_service
from app.utils.error_handler import get_logger, handle_api_error

# ルーター定義
router = APIRouter()
logger = get_logger(__name__)

# セキュリティ定数（Lint警告対応）
TOKEN_TYPE_BEARER = "bearer"  # nosec B105 # noqa: S105

# 依存関数（Lint警告対応）
db_dependency = Depends(get_db)
current_user_dependency = Depends(get_current_user)
form_dependency = Depends()


# レート制限ヘルパー
async def apply_login_rate_limit(request: Request) -> None:
    """ログイン用レート制限"""
    # クライアントIPを取得
    client_ip = "127.0.0.1"  # デフォルトIP

    if request.client is not None and hasattr(request.client, "host"):
        client_ip = request.client.host or "127.0.0.1"

    # X-Forwarded-For ヘッダーチェック（プロキシ経由時）
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        forwarded_ip = forwarded_for.split(",")[0].strip()
        if forwarded_ip:  # 空文字でない場合のみ使用
            client_ip = forwarded_ip

    is_allowed = await rate_limiter.is_allowed(
        key=client_ip, limit=settings.LOGIN_RATE_LIMIT_PER_MINUTE, window=60, identifier="login"
    )

    if not is_allowed:
        rate_info = await rate_limiter.get_remaining(client_ip, settings.LOGIN_RATE_LIMIT_PER_MINUTE, "login")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="ログイン試行回数が上限に達しました。しばらくお待ちください。",
            headers={
                "X-RateLimit-Limit": str(settings.LOGIN_RATE_LIMIT_PER_MINUTE),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(rate_info["reset_time"]),
                "Retry-After": str(rate_info["reset_time"]),
            },
        )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@handle_api_error("ユーザー登録")
async def register(user_in: UserCreate, db: AsyncSession = db_dependency) -> Any:
    """ユーザー登録

    新規ユーザーアカウントを作成
    """
    user = await auth_service.create_user(db, user_in)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=Token)
@handle_api_error("ユーザーログイン")
async def login(
    form_data: OAuth2PasswordRequestForm = form_dependency,
    db: AsyncSession = db_dependency,
    _: None = Depends(apply_login_rate_limit),
) -> Any:
    """ユーザーログイン

    メールアドレスとパスワードでログインし、アクセストークンを取得
    """
    # ユーザー認証
    user = await auth_service.authenticate_user(
        db,
        email=form_data.username,  # OAuth2仕様ではusernameフィールドを使用
        password=form_data.password,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # トークン生成
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security_manager.create_access_token(data={"sub": str(user.id)}, expires_delta=access_token_expires)

    refresh_token = security_manager.create_refresh_token(str(user.id))

    return Token(
        access_token=access_token,
        token_type=TOKEN_TYPE_BEARER,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=Token)
@handle_api_error("トークン更新")
async def refresh_token(refresh_data: RefreshTokenRequest, db: AsyncSession = db_dependency) -> Any:
    """トークン更新

    リフレッシュトークンを使用して新しいアクセストークンを取得
    """
    # リフレッシュトークン検証
    payload = await security_manager.verify_token(refresh_data.refresh_token)

    # トークンタイプチェック
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なトークンタイプです",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ユーザー取得
    from app.crud.user import user_crud

    user_id_raw = payload.get("sub")
    if user_id_raw is None or not isinstance(user_id_raw, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なユーザーIDです",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str = user_id_raw
    user = await user_crud.get(db, id=user_id)

    if not user or not user.can_login:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なユーザーです",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 古いリフレッシュトークンをブラックリスト
    await security_manager.blacklist_token(refresh_data.refresh_token)

    # 新しいトークン生成
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = security_manager.create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    new_refresh_token = security_manager.create_refresh_token(str(user.id))

    return Token(
        access_token=new_access_token,
        token_type=TOKEN_TYPE_BEARER,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=new_refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.put("/password", response_model=AuthResponse)
@handle_api_error("パスワード変更")
async def change_password(
    password_change: PasswordChangeRequest,
    current_user: User = current_user_dependency,
    db: AsyncSession = db_dependency,
) -> Any:
    """パスワード変更

    現在のパスワードを確認してから新しいパスワードに変更
    """
    # 現在のパスワード確認
    if not security_manager.verify_password(password_change.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="現在のパスワードが正しくありません",
        )

    # 新しいパスワードのハッシュ化
    new_password_hash = security_manager.get_password_hash(password_change.new_password)

    # パスワード更新
    from app.crud.user import user_crud

    await user_crud.update_password(db, user=current_user, password_hash=new_password_hash)

    return AuthResponse(success=True, message="パスワードが正常に変更されました", data=None)


@router.post("/logout", response_model=AuthResponse)
async def logout(
    request: Request,
    _: User = current_user_dependency,  # current_userは使用しないが認証チェックのため必要
) -> Any:
    """ログアウト

    現在のアクセストークンを無効化
    """
    try:
        # トークンを取得してブラックリスト化
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            await security_manager.blacklist_token(token)

        return AuthResponse(success=True, message="正常にログアウトしました", data=None)

    except Exception as e:
        logger.error(f"ログアウトエラー: {e}")
        # ログアウトは失敗してもクライアント側でトークンを削除すれば実質的に成功
        return AuthResponse(success=True, message="ログアウトしました", data=None)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = current_user_dependency) -> Any:
    """現在のユーザー情報取得"""
    return UserResponse.model_validate(current_user)


__all__ = ["router"]
