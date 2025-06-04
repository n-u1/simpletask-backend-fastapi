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
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    Token,
    UserCreate,
    UserResponse,
)
from app.services.auth import auth_service

# ルーター定義
router = APIRouter()

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
async def register(user_in: UserCreate, db: AsyncSession = db_dependency) -> Any:
    """ユーザー登録

    新規ユーザーアカウントを作成
    """
    try:
        user = await auth_service.create_user(db, user_in)
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"ユーザー登録エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="ユーザー登録中にエラーが発生しました"
        ) from e


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = form_dependency,
    db: AsyncSession = db_dependency,
    _: None = Depends(apply_login_rate_limit),
) -> Any:
    """ユーザーログイン

    メールアドレスとパスワードでログインし、アクセストークンを取得
    """
    try:
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
        access_token = security_manager.create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )

        refresh_token = security_manager.create_refresh_token(str(user.id))

        return Token(
            access_token=access_token,
            token_type=TOKEN_TYPE_BEARER,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user),
        )

    except HTTPException:
        raise
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"ログインエラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="ログイン処理中にエラーが発生しました"
        ) from e


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_data: RefreshTokenRequest, db: AsyncSession = db_dependency) -> Any:
    """トークン更新

    リフレッシュトークンを使用して新しいアクセストークンを取得
    """
    try:
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

    except HTTPException:
        raise
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"トークン更新エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なリフレッシュトークンです",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


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
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"ログアウトエラー: {e}")
        # ログアウトは失敗してもクライアント側でトークンを削除すれば実質的に成功
        return AuthResponse(success=True, message="ログアウトしました", data=None)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = current_user_dependency) -> Any:
    """現在のユーザー情報取得"""
    return UserResponse.model_validate(current_user)


@router.post("/change-password", response_model=AuthResponse)
async def change_password(
    password_data: PasswordChangeRequest, current_user: User = current_user_dependency, db: AsyncSession = db_dependency
) -> Any:
    """パスワード変更"""
    try:
        await auth_service.change_password(
            db,
            user=current_user,
            current_password=password_data.current_password,
            new_password=password_data.new_password,
        )

        return AuthResponse(success=True, message="パスワードが正常に変更されました", data=None)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"パスワード変更エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="パスワード変更中にエラーが発生しました"
        ) from e


@router.post("/password-reset-request", response_model=AuthResponse)
async def request_password_reset(reset_data: PasswordResetRequest, db: AsyncSession = db_dependency) -> Any:
    """パスワードリセット要求

    パスワードリセット用のトークンを生成
    """
    try:
        reset_token = await auth_service.generate_password_reset_token(db, email=reset_data.email)

        if reset_token:
            # TODO: メール送信の実装
            # await send_password_reset_email(reset_data.email, reset_token)
            pass

        # セキュリティのため、ユーザーが存在しない場合でも成功を返す
        return AuthResponse(
            success=True,
            message="パスワードリセットメールを送信しました（登録済みの場合）",
            data={"reset_token": reset_token} if settings.is_development else None,
        )

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"パスワードリセット要求エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="パスワードリセット要求の処理中にエラーが発生しました",
        ) from e


@router.post("/password-reset-confirm", response_model=AuthResponse)
async def confirm_password_reset(reset_data: PasswordResetConfirm, db: AsyncSession = db_dependency) -> Any:
    """パスワードリセット確認

    リセットトークンを使用してパスワードを変更
    """
    try:
        # トークンからメールアドレスは取得できないため、
        # 実際の実装ではトークンに含まれる情報から処理する
        success = await auth_service.reset_password(
            db,
            email="",  # 実装時はトークンから取得
            new_password=reset_data.new_password,
            reset_token=reset_data.token,
        )

        if not success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無効なリセットトークンです")

        return AuthResponse(success=True, message="パスワードが正常にリセットされました", data=None)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"パスワードリセット確認エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="パスワードリセット中にエラーが発生しました"
        ) from e


# ルーターのエクスポート確認
__all__ = ["router"]
