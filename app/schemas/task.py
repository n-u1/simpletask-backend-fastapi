"""タスク関連のPydanticスキーマ

タスクの作成、更新、応答のリクエスト・レスポンススキーマを提供
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import ErrorMessages, TaskConstants, TaskPriority, TaskStatus


class TaskBase(BaseModel):
    """タスクベーススキーマ（共通フィールド）"""

    title: str = Field(
        ...,
        min_length=TaskConstants.TITLE_MIN_LENGTH,
        max_length=TaskConstants.TITLE_MAX_LENGTH,
        description="タスクタイトル",
        examples=["API設計書を作成する"],
    )

    description: str | None = Field(
        None,
        max_length=TaskConstants.DESCRIPTION_MAX_LENGTH,
        description="タスクの詳細説明",
        examples=["認証APIの設計書をOpenAPI形式で作成する"],
    )

    status: TaskStatus = Field(default=TaskStatus.TODO, description="タスクステータス", examples=[TaskStatus.TODO])

    priority: TaskPriority = Field(
        default=TaskPriority.MEDIUM, description="タスク優先度", examples=[TaskPriority.HIGH]
    )

    due_date: datetime | None = Field(None, description="期限日時（UTC）", examples=["2025-06-10T15:00:00Z"])

    position: int = Field(
        default=TaskConstants.DEFAULT_POSITION,
        ge=TaskConstants.POSITION_MIN,
        le=TaskConstants.POSITION_MAX,
        description="表示順序",
        examples=[0],
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        v = v.strip()

        if len(v) < TaskConstants.TITLE_MIN_LENGTH:
            raise ValueError(ErrorMessages.TASK_TITLE_REQUIRED)

        if len(v) > TaskConstants.TITLE_MAX_LENGTH:
            raise ValueError(ErrorMessages.TASK_TITLE_TOO_LONG)

        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str | None) -> str | None:
        if v is None:
            return None

        v = v.strip()
        if not v:
            return None

        if len(v) > TaskConstants.DESCRIPTION_MAX_LENGTH:
            raise ValueError(f"説明は{TaskConstants.DESCRIPTION_MAX_LENGTH}文字以内で入力してください")

        return v


class TaskCreate(TaskBase):
    """タスク作成リクエストスキーマ"""

    tag_ids: list[UUID] = Field(
        default_factory=list,
        description="関連付けるタグのIDリスト",
        examples=[["550e8400-e29b-41d4-a716-446655440001"]],
    )

    @field_validator("tag_ids")
    @classmethod
    def validate_tag_ids(cls, v: list[UUID]) -> list[UUID]:
        # 重複を除去
        unique_ids = list(dict.fromkeys(v))

        # 最大関連付け数の制限（必要に応じて）
        max_tags = 10
        if len(unique_ids) > max_tags:
            raise ValueError(f"タグは最大{max_tags}個まで関連付けできます")

        return unique_ids


class TaskUpdate(BaseModel):
    """タスク更新リクエストスキーマ（部分更新対応）"""

    title: str | None = Field(
        None,
        min_length=TaskConstants.TITLE_MIN_LENGTH,
        max_length=TaskConstants.TITLE_MAX_LENGTH,
        description="タスクタイトル",
    )

    description: str | None = Field(
        None, max_length=TaskConstants.DESCRIPTION_MAX_LENGTH, description="タスクの詳細説明"
    )

    status: TaskStatus | None = Field(None, description="タスクステータス")

    priority: TaskPriority | None = Field(None, description="タスク優先度")

    due_date: datetime | None = Field(None, description="期限日時（UTC）")

    position: int | None = Field(
        None, ge=TaskConstants.POSITION_MIN, le=TaskConstants.POSITION_MAX, description="表示順序"
    )

    tag_ids: list[UUID] | None = Field(None, description="関連付けるタグのIDリスト（完全置換）")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str | None:
        if v is None:
            return None

        v = v.strip()

        if len(v) < TaskConstants.TITLE_MIN_LENGTH:
            raise ValueError(ErrorMessages.TASK_TITLE_REQUIRED)

        if len(v) > TaskConstants.TITLE_MAX_LENGTH:
            raise ValueError(ErrorMessages.TASK_TITLE_TOO_LONG)

        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str | None) -> str | None:
        if v is None:
            return None

        v = v.strip()
        if not v:
            return None

        if len(v) > TaskConstants.DESCRIPTION_MAX_LENGTH:
            raise ValueError(f"説明は{TaskConstants.DESCRIPTION_MAX_LENGTH}文字以内で入力してください")

        return v

    @field_validator("tag_ids")
    @classmethod
    def validate_tag_ids(cls, v: list[UUID] | None) -> list[UUID] | None:
        if v is None:
            return None

        # 重複を除去
        unique_ids = list(dict.fromkeys(v))

        # 最大関連付け数の制限
        max_tags = 10
        if len(unique_ids) > max_tags:
            raise ValueError(f"タグは最大{max_tags}個まで関連付けできます")

        return unique_ids


class TaskStatusUpdate(BaseModel):
    """タスクステータス変更専用スキーマ"""

    status: TaskStatus = Field(..., description="新しいタスクステータス")


class TaskPositionUpdate(BaseModel):
    """タスク位置変更スキーマ（ドラッグ&ドロップ用）"""

    task_id: UUID = Field(..., description="移動するタスクID")

    new_status: TaskStatus | None = Field(None, description="新しいステータス（カンバン間移動時）")

    new_position: int = Field(
        ..., ge=TaskConstants.POSITION_MIN, le=TaskConstants.POSITION_MAX, description="新しい位置"
    )

    affected_tasks: list["TaskPositionItem"] = Field(default_factory=list, description="位置が影響を受ける他のタスク")


class TaskPositionItem(BaseModel):
    """位置変更で影響を受けるタスクの情報"""

    id: UUID = Field(..., description="タスクID")
    position: int = Field(..., ge=TaskConstants.POSITION_MIN, le=TaskConstants.POSITION_MAX, description="新しい位置")


class TagInfo(BaseModel):
    """タスク応答に含まれるタグ情報"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="タグID")
    name: str = Field(..., description="タグ名")
    color: str = Field(..., description="タグ色")


class TaskResponse(TaskBase):
    """タスク応答スキーマ"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="タスクID")
    user_id: UUID = Field(..., description="所有者ID")
    completed_at: datetime | None = Field(None, description="完了日時")
    tags: list[TagInfo] = Field(default_factory=list, description="関連タグ")

    # 計算プロパティ
    is_completed: bool = Field(..., description="完了済みフラグ")
    is_archived: bool = Field(..., description="アーカイブ済みフラグ")
    is_overdue: bool = Field(..., description="期限切れフラグ")
    days_until_due: int | None = Field(None, description="期限までの日数")
    tag_names: list[str] = Field(default_factory=list, description="タグ名リスト")

    created_at: datetime = Field(..., description="作成日時")
    updated_at: datetime = Field(..., description="更新日時")


class TaskListResponse(BaseModel):
    """タスク一覧応答スキーマ"""

    tasks: list[TaskResponse] = Field(..., description="タスクリスト")
    total: int = Field(..., description="総件数")
    page: int = Field(..., description="現在のページ")
    per_page: int = Field(..., description="1ページあたりの件数")
    total_pages: int = Field(..., description="総ページ数")


class TaskFilters(BaseModel):
    """タスクフィルタリング用スキーマ"""

    status: list[TaskStatus] | None = Field(None, description="ステータスフィルタ")

    priority: list[TaskPriority] | None = Field(None, description="優先度フィルタ")

    tag_ids: list[UUID] | None = Field(None, description="タグIDフィルタ")

    tag_names: list[str] | None = Field(None, description="タグ名フィルタ")

    due_date_from: datetime | None = Field(None, description="期限日時の開始範囲")

    due_date_to: datetime | None = Field(None, description="期限日時の終了範囲")

    is_overdue: bool | None = Field(None, description="期限切れタスクのみ")

    search: str | None = Field(None, min_length=1, max_length=100, description="タイトル・説明での検索")

    @field_validator("search")
    @classmethod
    def validate_search(cls, v: str | None) -> str | None:
        if v is None:
            return None

        v = v.strip()
        if not v:
            return None

        return v


class TaskSortOptions(BaseModel):
    """タスクソート用スキーマ"""

    sort_by: str = Field(default="created_at", description="ソートフィールド")

    order: str = Field(default="desc", description="ソート順序（asc/desc）")

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v: str) -> str:
        from app.core.constants import APIConstants

        if v not in APIConstants.TASK_SORTABLE_FIELDS:
            raise ValueError(
                f"ソートフィールドは次のいずれかを指定してください: {', '.join(APIConstants.TASK_SORTABLE_FIELDS)}"
            )

        return v

    @field_validator("order")
    @classmethod
    def validate_order(cls, v: str) -> str:
        from app.core.constants import APIConstants

        if v not in APIConstants.ALLOWED_SORT_ORDERS:
            raise ValueError(
                f"ソート順序は次のいずれかを指定してください: {', '.join(APIConstants.ALLOWED_SORT_ORDERS)}"
            )

        return v


# スキーマの使用例とドキュメント用の設定
class TaskSchemaExamples:
    """タスクスキーマの使用例"""

    CREATE_EXAMPLE = {
        "title": "API設計書を作成する",
        "description": "認証APIの設計書をOpenAPI形式で作成する",
        "status": "todo",
        "priority": "high",
        "due_date": "2025-06-10T15:00:00Z",
        "tag_ids": ["550e8400-e29b-41d4-a716-446655440001"],
    }

    UPDATE_EXAMPLE = {
        "status": "in_progress",
        "priority": "urgent",
        "description": "認証APIの設計書をOpenAPI形式で作成する（修正）",
    }

    FILTER_EXAMPLE = {
        "status": ["todo", "in_progress"],
        "priority": ["high", "urgent"],
        "tag_names": ["開発", "緊急"],
        "search": "API",
    }
