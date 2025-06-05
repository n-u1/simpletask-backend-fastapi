"""ユーザー関連のPydanticスキーマ

ユーザープロフィール管理のリクエスト・レスポンススキーマを提供
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.constants import ErrorMessages, UserConstants, validate_image_url


class UserBase(BaseModel):
    """ユーザーベーススキーマ（共通フィールド）"""

    email: EmailStr = Field(..., description="メールアドレス", examples=["user@example.com"])

    display_name: str = Field(
        ...,
        min_length=UserConstants.DISPLAY_NAME_MIN_LENGTH,
        max_length=UserConstants.DISPLAY_NAME_MAX_LENGTH,
        description="表示名",
        examples=["山田太郎"],
    )

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: str) -> str:
        v = v.strip()

        if len(v) < UserConstants.DISPLAY_NAME_MIN_LENGTH:
            raise ValueError(ErrorMessages.DISPLAY_NAME_TOO_SHORT)

        if len(v) > UserConstants.DISPLAY_NAME_MAX_LENGTH:
            raise ValueError(ErrorMessages.DISPLAY_NAME_TOO_LONG)

        if not UserConstants.DISPLAY_NAME_PATTERN.match(v):
            raise ValueError(ErrorMessages.DISPLAY_NAME_INVALID_CHARS)

        return v


class UserUpdate(BaseModel):
    """ユーザー情報更新リクエストスキーマ（部分更新対応）"""

    display_name: str | None = Field(
        None,
        min_length=UserConstants.DISPLAY_NAME_MIN_LENGTH,
        max_length=UserConstants.DISPLAY_NAME_MAX_LENGTH,
        description="表示名",
        examples=["山田次郎"],
    )

    avatar_url: str | None = Field(
        None,
        max_length=UserConstants.AVATAR_URL_MAX_LENGTH,
        description="アバター画像URL",
        examples=["https://example.com/avatar.jpg"],
    )

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: str | None) -> str | None:
        if v is None:
            return v

        v = v.strip()

        if len(v) < UserConstants.DISPLAY_NAME_MIN_LENGTH:
            raise ValueError(ErrorMessages.DISPLAY_NAME_TOO_SHORT)

        if len(v) > UserConstants.DISPLAY_NAME_MAX_LENGTH:
            raise ValueError(ErrorMessages.DISPLAY_NAME_TOO_LONG)

        if not UserConstants.DISPLAY_NAME_PATTERN.match(v):
            raise ValueError(ErrorMessages.DISPLAY_NAME_INVALID_CHARS)

        return v

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return None

        v = v.strip()

        if not validate_image_url(v):
            raise ValueError("有効な画像ファイル（jpg, jpeg, png, gif, webp）のURLを入力してください")

        return v


class UserResponse(BaseModel):
    """ユーザー情報レスポンススキーマ"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="ユーザーID")
    email: EmailStr = Field(..., description="メールアドレス")
    display_name: str = Field(..., description="表示名")
    avatar_url: str | None = Field(None, description="アバター画像URL")
    is_active: bool = Field(..., description="アクティブ状態")
    is_verified: bool = Field(..., description="メール認証状態")
    created_at: datetime = Field(..., description="作成日時")
    updated_at: datetime = Field(..., description="更新日時")
    last_login_at: datetime | None = Field(None, description="最終ログイン日時")


class UserProfileSummary(BaseModel):
    """ユーザープロフィール要約スキーマ（他の機能での参照用）"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="ユーザーID")
    display_name: str = Field(..., description="表示名")
    avatar_url: str | None = Field(None, description="アバター画像URL")


# スキーマの使用例とドキュメント用の設定
class UserSchemaExamples:
    """ユーザースキーマの使用例"""

    UPDATE_EXAMPLE = {"display_name": "田中花子", "avatar_url": "https://example.com/avatar/tanaka.jpg"}

    RESPONSE_EXAMPLE = {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "user@example.com",
        "display_name": "山田太郎",
        "avatar_url": "https://example.com/avatar.jpg",
        "is_active": True,
        "is_verified": False,
        "created_at": "2025-06-02T10:00:00Z",
        "updated_at": "2025-06-02T10:00:00Z",
        "last_login_at": "2025-06-02T12:00:00Z",
    }
