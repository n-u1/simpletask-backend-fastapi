"""タグAPIエンドポイント

タグの作成、取得、更新、削除のREST APIを提供
"""

# FastAPIの依存注入システム（Depends, Query）はLint警告の対象外とする
# ruff: noqa: B008

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import APIConstants, ErrorMessages
from app.core.database import get_db
from app.core.security import get_current_user
from app.dtos.tag import TagDTO, TagListDTO
from app.models.user import User
from app.schemas.tag import (
    TagCreate,
    TagFilters,
    TagListResponse,
    TagResponse,
    TagSortOptions,
    TagUpdate,
)
from app.services.tag import tag_service

router = APIRouter()


def _convert_tag_dto_to_response(tag_dto: TagDTO) -> TagResponse:
    """TagDTOをTagResponseに変換"""
    return TagResponse(
        id=tag_dto.id,
        user_id=tag_dto.user_id,
        name=tag_dto.name,
        color=tag_dto.color,
        description=tag_dto.description,
        is_active=tag_dto.is_active,
        task_count=tag_dto.task_count,
        active_task_count=tag_dto.active_task_count,
        completed_task_count=tag_dto.completed_task_count,
        color_rgb=tag_dto.color_rgb,
        is_preset_color=tag_dto.is_preset_color,
        created_at=tag_dto.created_at,
        updated_at=tag_dto.updated_at,
    )


def _convert_tag_list_dto_to_response(tag_list_dto: TagListDTO) -> TagListResponse:
    """TagListDTOをTagListResponseに変換"""
    return TagListResponse(
        tags=[_convert_tag_dto_to_response(tag_dto) for tag_dto in tag_list_dto.tags],
        total=tag_list_dto.total,
        page=tag_list_dto.page,
        per_page=tag_list_dto.per_page,
        total_pages=tag_list_dto.total_pages,
    )


@router.get("/", response_model=TagListResponse)
async def get_tags(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    # ページネーション
    page: int = Query(default=1, ge=1, description="ページ番号"),
    per_page: int = Query(
        default=APIConstants.DEFAULT_PAGE_SIZE,
        ge=APIConstants.MIN_PAGE_SIZE,
        le=APIConstants.MAX_PAGE_SIZE,
        description="1ページあたりの件数",
    ),
    # フィルタリング
    is_active: bool | None = Query(default=None, description="アクティブ状態フィルタ"),
    colors: list[str] | None = Query(default=None, description="カラーフィルタ"),
    has_tasks: bool | None = Query(default=None, description="タスク有無フィルタ"),
    search: str | None = Query(default=None, min_length=1, max_length=100, description="検索キーワード"),
    # ソート
    sort_by: str = Query(default="created_at", description="ソートフィールド"),
    order: str = Query(default="desc", description="ソート順序（asc/desc）"),
    # その他
    include_inactive: bool = Query(default=False, description="非アクティブタグを含める"),
) -> TagListResponse:
    """タグ一覧を取得"""
    filters = TagFilters(is_active=is_active, colors=colors, has_tasks=has_tasks, min_task_count=None, search=search)

    sort_options = TagSortOptions(sort_by=sort_by, order=order)

    try:
        # サービス層からDTOを取得
        tag_list_dto = await tag_service.get_tags(
            db,
            current_user.id,
            page=page,
            per_page=per_page,
            filters=filters,
            sort_options=sort_options,
            include_inactive=include_inactive,
        )

        return _convert_tag_list_dto_to_response(tag_list_dto)

    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/", response_model=TagResponse, status_code=http_status.HTTP_201_CREATED)
async def create_tag(
    *, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user), tag_in: TagCreate
) -> TagResponse:
    """タグを作成"""
    try:
        # サービス層でタグ作成
        tag_dto = await tag_service.create_tag(db, tag_in, current_user.id)

        return _convert_tag_dto_to_response(tag_dto)

    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorMessages.SERVER_ERROR
        ) from e


@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tag_id: UUID,
) -> TagResponse:
    """特定タグを取得"""
    try:
        # サービス層からDTOを取得
        tag_dto = await tag_service.get_tag(db, tag_id, current_user.id)
        if not tag_dto:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=ErrorMessages.TAG_NOT_FOUND)

        return _convert_tag_dto_to_response(tag_dto)

    except PermissionError as e:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.put("/{tag_id}", response_model=TagResponse)
async def update_tag(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tag_id: UUID,
    tag_in: TagUpdate,
) -> TagResponse:
    """タグを更新"""
    try:
        # サービス層でタグ更新
        tag_dto = await tag_service.update_tag(db, tag_id, tag_in, current_user.id)

        return _convert_tag_dto_to_response(tag_dto)

    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.delete("/{tag_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_tag(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tag_id: UUID,
) -> None:
    """タグを削除"""
    try:
        success = await tag_service.delete_tag(db, tag_id, current_user.id)
        if not success:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=ErrorMessages.TAG_NOT_FOUND)

    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=str(e)) from e
