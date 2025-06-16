"""ユーザーAPIエンドポイント

ユーザープロフィール管理のREST APIを提供
"""

# FastAPIの依存注入システム（Depends, Query）はLint警告の対象外とする
# ruff: noqa: B008

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ErrorMessages
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.services.user import user_service

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(*, current_user: User = Depends(get_current_user)) -> UserResponse:
    """現在のユーザープロフィールを取得

    注意: get_current_userから直接SQLAlchemyモデルを受け取るため、ここでPydanticレスポンスモデルに変換する
    """
    # SQLAlchemyモデルからPydanticレスポンスモデルに変換
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    *, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user), user_update: UserUpdate
) -> UserResponse:
    """ユーザープロフィールを更新"""
    try:
        # サービス層でプロフィール更新
        user_response = await user_service.update_user_profile(db, current_user.id, user_update)

        return user_response

    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorMessages.SERVER_ERROR
        ) from e


@router.delete("/me", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_user_account(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    permanent: bool = Query(default=False, description="物理削除フラグ（true: 完全削除、false: アカウント無効化）"),
) -> None:
    """ユーザーアカウントを削除

    - permanent=false: アカウント無効化（復元可能）
    - permanent=true: 完全削除（復元不可、すべてのデータが削除）
    """
    try:
        success = await user_service.delete_user_account(db, current_user.id, permanent=permanent)

        if not success:
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail="アカウント削除に失敗しました"
            )

    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorMessages.SERVER_ERROR
        ) from e
