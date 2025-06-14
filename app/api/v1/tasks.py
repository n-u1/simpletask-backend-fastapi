"""タスクAPIエンドポイント

タスクの作成、取得、更新、削除のREST APIを提供
"""

# FastAPIの依存注入システム（Depends, Query）はLint警告の対象外とする
# ruff: noqa: B008

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import APIConstants, ErrorMessages, TaskPriority, TaskStatus
from app.core.database import get_db
from app.core.security import get_current_user
from app.dtos.task import TaskDTO, TaskListDTO
from app.models.user import User
from app.schemas.task import (
    TagInfo,
    TaskCreate,
    TaskFilters,
    TaskListResponse,
    TaskPositionUpdate,
    TaskResponse,
    TaskSortOptions,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.services.task import task_service

router = APIRouter()


def _convert_task_dto_to_response(task_dto: TaskDTO) -> TaskResponse:
    """TaskDTOをTaskResponseに変換"""
    return TaskResponse(
        id=task_dto.id,
        user_id=task_dto.user_id,
        title=task_dto.title,
        description=task_dto.description,
        status=TaskStatus(task_dto.status),
        priority=TaskPriority(task_dto.priority),
        due_date=task_dto.due_date,
        completed_at=task_dto.completed_at,
        position=task_dto.position,
        tags=[
            TagInfo(
                id=tag.id,
                name=tag.name,
                color=tag.color,
                description=tag.description,
            )
            for tag in task_dto.tags
        ],
        is_completed=task_dto.is_completed,
        is_archived=task_dto.is_archived,
        is_overdue=task_dto.is_overdue,
        days_until_due=task_dto.days_until_due,
        tag_names=task_dto.tag_names,
        created_at=task_dto.created_at,
        updated_at=task_dto.updated_at,
    )


def _convert_task_list_dto_to_response(task_list_dto: TaskListDTO) -> TaskListResponse:
    """TaskListDTOをTaskListResponseに変換"""
    return TaskListResponse(
        tasks=[_convert_task_dto_to_response(task_dto) for task_dto in task_list_dto.tasks],
        total=task_list_dto.total,
        page=task_list_dto.page,
        per_page=task_list_dto.per_page,
        total_pages=task_list_dto.total_pages,
    )


@router.get("/", response_model=TaskListResponse)
async def get_tasks(
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
    status: list[TaskStatus] | None = Query(default=None, description="ステータスフィルタ"),
    priority: list[TaskPriority] | None = Query(default=None, description="優先度フィルタ"),
    tag_ids: list[UUID] | None = Query(default=None, description="タグIDフィルタ"),
    tag_names: list[str] | None = Query(default=None, description="タグ名フィルタ"),
    is_overdue: bool | None = Query(default=None, description="期限切れフィルタ"),
    search: str | None = Query(default=None, min_length=1, max_length=100, description="検索キーワード"),
    # ソート
    sort_by: str = Query(default="created_at", description="ソートフィールド"),
    order: str = Query(default="desc", description="ソート順序（asc/desc）"),
) -> TaskListResponse:
    """タスク一覧を取得"""
    filters = TaskFilters(
        status=status,
        priority=priority,
        tag_ids=tag_ids,
        tag_names=tag_names,
        due_date_from=None,
        due_date_to=None,
        is_overdue=is_overdue,
        search=search,
    )

    sort_options = TaskSortOptions(sort_by=sort_by, order=order)

    try:
        # サービス層からDTOを取得
        task_list_dto = await task_service.get_tasks(
            db,
            current_user.id,
            page=page,
            per_page=per_page,
            filters=filters,
            sort_options=sort_options,
        )

        return _convert_task_list_dto_to_response(task_list_dto)

    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/", response_model=TaskResponse, status_code=http_status.HTTP_201_CREATED)
async def create_task(
    *, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user), task_in: TaskCreate
) -> TaskResponse:
    """タスクを作成"""
    try:
        # サービス層でタスク作成
        task_dto = await task_service.create_task(db, task_in, current_user.id)

        return _convert_task_dto_to_response(task_dto)

    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorMessages.SERVER_ERROR
        ) from e


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    *, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user), task_id: UUID
) -> TaskResponse:
    """特定タスクを取得"""
    try:
        # サービス層からDTOを取得
        task_dto = await task_service.get_task(db, task_id, current_user.id)
        if not task_dto:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=ErrorMessages.TASK_NOT_FOUND)

        return _convert_task_dto_to_response(task_dto)

    except PermissionError as e:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    task_id: UUID,
    task_in: TaskUpdate,
) -> TaskResponse:
    """タスクを更新"""
    try:
        # サービス層でタスク更新
        task_dto = await task_service.update_task(db, task_id, task_in, current_user.id)

        return _convert_task_dto_to_response(task_dto)

    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.patch("/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    task_id: UUID,
    status_update: TaskStatusUpdate,
) -> TaskResponse:
    """タスクステータスを更新"""
    try:
        # サービス層でステータス更新
        task_dto = await task_service.update_task_status(db, task_id, status_update.status, current_user.id)

        return _convert_task_dto_to_response(task_dto)

    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.delete("/{task_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_task(
    *, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user), task_id: UUID
) -> None:
    """タスクを削除"""
    try:
        success = await task_service.delete_task(db, task_id, current_user.id)
        if not success:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=ErrorMessages.TASK_NOT_FOUND)

    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.patch("/reorder", response_model=dict[str, str | list | int])
async def reorder_tasks(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    position_update: TaskPositionUpdate,
) -> dict[str, str | list | int]:
    """タスクの並び順を変更（ドラッグ&ドロップ用）"""
    try:
        success = await task_service.reorder_tasks(db, position_update, current_user.id)

        if not success:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="タスクの並び順変更に失敗しました")

        # 成功時は更新後のタスク一覧を返す（フロントエンドでの同期用）
        updated_task_list_dto = await task_service.get_tasks(
            db,
            current_user.id,
            page=1,
            per_page=100,  # 十分な数を取得
            filters=None,
            sort_options=TaskSortOptions(sort_by="position", order="asc"),
        )

        return {
            "message": "タスクの並び順を変更しました",
            "tasks": [_convert_task_dto_to_response(task_dto).model_dump() for task_dto in updated_task_list_dto.tasks],
            "total": updated_task_list_dto.total,
        }

    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.get("/status/{task_status}", response_model=list[TaskResponse])
async def get_tasks_by_status(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    task_status: TaskStatus,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(
        default=APIConstants.DEFAULT_PAGE_SIZE, ge=APIConstants.MIN_PAGE_SIZE, le=APIConstants.MAX_PAGE_SIZE
    ),
) -> list[TaskResponse]:
    """ステータス別でタスクを取得"""
    try:
        # サービス層からDTOリストを取得
        task_dtos = await task_service.get_tasks_by_status(
            db, current_user.id, task_status, page=page, per_page=per_page
        )

        return [_convert_task_dto_to_response(task_dto) for task_dto in task_dtos]

    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/overdue/list", response_model=list[TaskResponse])
async def get_overdue_tasks(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(
        default=APIConstants.DEFAULT_PAGE_SIZE, ge=APIConstants.MIN_PAGE_SIZE, le=APIConstants.MAX_PAGE_SIZE
    ),
) -> list[TaskResponse]:
    """期限切れタスクを取得"""
    try:
        # サービス層からDTOリストを取得
        task_dtos = await task_service.get_overdue_tasks(db, current_user.id, page=page, per_page=per_page)

        return [_convert_task_dto_to_response(task_dto) for task_dto in task_dtos]

    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
