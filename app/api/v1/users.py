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
from app.dtos.user import UserDTO
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.services.user import user_service

router = APIRouter()


def _convert_user_dto_to_response(user_dto: UserDTO) -> UserResponse:
    """UserDTOをUserResponseに変換"""
    return UserResponse(
        id=user_dto.id,
        email=user_dto.email,
        display_name=user_dto.display_name,
        avatar_url=user_dto.avatar_url,
        is_active=user_dto.is_active,
        is_verified=user_dto.is_verified,
        created_at=user_dto.created_at,
        updated_at=user_dto.updated_at,
        last_login_at=user_dto.last_login_at,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(*, current_user: User = Depends(get_current_user)) -> UserResponse:
    """現在のユーザープロフィールを取得

    注意: get_current_userから直接SQLAlchemyモデルを受け取るため、ここでDTOに変換する
    """
    # SQLAlchemyモデルからDTOに変換
    user_dto = UserDTO(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        avatar_url=current_user.avatar_url,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        last_login_at=current_user.last_login_at,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )

    return _convert_user_dto_to_response(user_dto)


@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    *, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user), user_update: UserUpdate
) -> UserResponse:
    """ユーザープロフィールを更新"""
    try:
        # サービス層でプロフィール更新
        user_dto = await user_service.update_user_profile(db, current_user.id, user_update)

        return _convert_user_dto_to_response(user_dto)

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
