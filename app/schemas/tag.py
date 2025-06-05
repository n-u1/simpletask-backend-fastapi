"""タグ関連のPydanticスキーマ

タグの作成、更新、応答のリクエスト・レスポンススキーマを提供
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import ErrorMessages, TagConstants, validate_color_code


class TagBase(BaseModel):
    """タグベーススキーマ（共通フィールド）"""

    name: str = Field(
        ...,
        min_length=TagConstants.NAME_MIN_LENGTH,
        max_length=TagConstants.NAME_MAX_LENGTH,
        description="タグ名",
        examples=["開発"],
    )

    color: str = Field(
        default=TagConstants.DEFAULT_COLOR, description="タグの表示色（16進数カラーコード）", examples=["#3B82F6"]
    )

    description: str | None = Field(
        None, max_length=TagConstants.DESCRIPTION_MAX_LENGTH, description="タグの説明", examples=["開発関連のタスク"]
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()

        if len(v) < TagConstants.NAME_MIN_LENGTH:
            raise ValueError(ErrorMessages.TAG_NAME_REQUIRED)

        if len(v) > TagConstants.NAME_MAX_LENGTH:
            raise ValueError(ErrorMessages.TAG_NAME_TOO_LONG)

        return v

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        if not v:
            return TagConstants.DEFAULT_COLOR

        v = v.strip().upper()

        if not v.startswith("#"):
            v = f"#{v}"

        if not validate_color_code(v):
            raise ValueError(ErrorMessages.TAG_COLOR_INVALID)

        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str | None) -> str | None:
        if v is None:
            return None

        v = v.strip()
        if not v:
            return None

        if len(v) > TagConstants.DESCRIPTION_MAX_LENGTH:
            raise ValueError(f"タグ説明は{TagConstants.DESCRIPTION_MAX_LENGTH}文字以内で入力してください")

        return v


class TagCreate(TagBase):
    """タグ作成リクエストスキーマ"""

    pass


class TagUpdate(BaseModel):
    """タグ更新リクエストスキーマ（部分更新対応）"""

    name: str | None = Field(
        None, min_length=TagConstants.NAME_MIN_LENGTH, max_length=TagConstants.NAME_MAX_LENGTH, description="タグ名"
    )

    color: str | None = Field(None, description="タグの表示色（16進数カラーコード）")

    description: str | None = Field(None, max_length=TagConstants.DESCRIPTION_MAX_LENGTH, description="タグの説明")

    is_active: bool | None = Field(None, description="アクティブフラグ")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is None:
            return None

        v = v.strip()

        if len(v) < TagConstants.NAME_MIN_LENGTH:
            raise ValueError(ErrorMessages.TAG_NAME_REQUIRED)

        if len(v) > TagConstants.NAME_MAX_LENGTH:
            raise ValueError(ErrorMessages.TAG_NAME_TOO_LONG)

        return v

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        if v is None:
            return None

        v = v.strip().upper()

        if not v.startswith("#"):
            v = f"#{v}"

        if not validate_color_code(v):
            raise ValueError(ErrorMessages.TAG_COLOR_INVALID)

        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str | None) -> str | None:
        if v is None:
            return None

        v = v.strip()
        if not v:
            return None

        if len(v) > TagConstants.DESCRIPTION_MAX_LENGTH:
            raise ValueError(f"タグ説明は{TagConstants.DESCRIPTION_MAX_LENGTH}文字以内で入力してください")

        return v


class TagResponse(TagBase):
    """タグ応答スキーマ"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="タグID")
    user_id: UUID = Field(..., description="所有者ID")
    is_active: bool = Field(..., description="アクティブフラグ")

    # 計算プロパティ
    task_count: int = Field(..., description="関連タスク数")
    active_task_count: int = Field(..., description="アクティブタスク数")
    completed_task_count: int = Field(..., description="完了済みタスク数")
    color_rgb: tuple[int, int, int] = Field(..., description="RGB値")
    is_preset_color: bool = Field(..., description="プリセット色フラグ")

    created_at: datetime = Field(..., description="作成日時")
    updated_at: datetime = Field(..., description="更新日時")


class TagListResponse(BaseModel):
    """タグ一覧応答スキーマ"""

    tags: list[TagResponse] = Field(..., description="タグリスト")
    total: int = Field(..., description="総件数")
    page: int = Field(..., description="現在のページ")
    per_page: int = Field(..., description="1ページあたりの件数")
    total_pages: int = Field(..., description="総ページ数")


class TagFilters(BaseModel):
    """タグフィルタリング用スキーマ"""

    is_active: bool | None = Field(None, description="アクティブ状態フィルタ")

    colors: list[str] | None = Field(None, description="カラーフィルタ")

    has_tasks: bool | None = Field(None, description="タスクありフィルタ")

    min_task_count: int | None = Field(None, ge=0, description="最小タスク数")

    search: str | None = Field(None, min_length=1, max_length=100, description="タグ名・説明での検索")

    @field_validator("colors")
    @classmethod
    def validate_colors(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None

        validated_colors = []
        for color in v:
            color = color.strip().upper()
            if not color.startswith("#"):
                color = f"#{color}"

            if validate_color_code(color):
                validated_colors.append(color)

        return validated_colors if validated_colors else None

    @field_validator("search")
    @classmethod
    def validate_search(cls, v: str | None) -> str | None:
        if v is None:
            return None

        v = v.strip()
        if not v:
            return None

        return v


class TagSortOptions(BaseModel):
    """タグソート用スキーマ"""

    sort_by: str = Field(default="created_at", description="ソートフィールド")

    order: str = Field(default="desc", description="ソート順序（asc/desc）")

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v: str) -> str:
        from app.core.constants import APIConstants

        if v not in APIConstants.TAG_SORTABLE_FIELDS:
            raise ValueError(
                f"ソートフィールドは次のいずれかを指定してください: {', '.join(APIConstants.TAG_SORTABLE_FIELDS)}"
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
class TagSchemaExamples:
    """タグスキーマの使用例"""

    CREATE_EXAMPLE = {"name": "開発", "color": "#3B82F6", "description": "開発関連のタスク"}

    UPDATE_EXAMPLE = {"name": "緊急開発", "color": "#EF4444", "description": "緊急対応が必要な開発タスク"}

    FILTER_EXAMPLE = {"is_active": True, "colors": ["#3B82F6", "#EF4444"], "has_tasks": True, "search": "開発"}
