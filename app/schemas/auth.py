import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.constants import ErrorMessages, UserConstants, is_weak_password


class UserCreate(BaseModel):
    """ユーザー作成（登録）リクエストスキーマ"""

    email: EmailStr = Field(..., description="メールアドレス", examples=["user@example.com"])

    password: str = Field(
        ...,
        min_length=UserConstants.PASSWORD_MIN_LENGTH,
        max_length=UserConstants.PASSWORD_MAX_LENGTH,
        description="パスワード（8文字以上）",
        examples=["SecurePassword123!"],
    )

    display_name: str = Field(
        ...,
        min_length=UserConstants.DISPLAY_NAME_MIN_LENGTH,
        max_length=UserConstants.DISPLAY_NAME_MAX_LENGTH,
        description="表示名",
        examples=["山田太郎"],
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < UserConstants.PASSWORD_MIN_LENGTH:
            raise ValueError(ErrorMessages.PASSWORD_TOO_SHORT)

        if len(v) > UserConstants.PASSWORD_MAX_LENGTH:
            raise ValueError(ErrorMessages.PASSWORD_TOO_LONG)

        if not re.search(r"[A-Za-z]", v):
            raise ValueError(ErrorMessages.PASSWORD_NO_LETTERS)

        if not re.search(r"\d", v):
            raise ValueError(ErrorMessages.PASSWORD_NO_NUMBERS)

        if is_weak_password(v):
            raise ValueError(ErrorMessages.PASSWORD_TOO_WEAK)

        return v

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


class UserLogin(BaseModel):
    """ログインリクエストスキーマ"""

    email: EmailStr = Field(..., description="メールアドレス", examples=["user@example.com"])

    password: str = Field(
        ...,
        min_length=1,
        max_length=UserConstants.PASSWORD_MAX_LENGTH,
        description="パスワード",
        examples=["SecurePassword123!"],
    )


class UserResponse(BaseModel):
    """ユーザー情報レスポンススキーマ（認証関連で使用）"""

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


class Token(BaseModel):
    """認証トークンレスポンススキーマ"""

    access_token: str = Field(..., description="アクセストークン")
    token_type: str = Field(default="bearer", description="トークンタイプ")
    expires_in: int = Field(..., description="有効期限（秒）")
    refresh_token: str | None = Field(None, description="リフレッシュトークン")
    user: UserResponse = Field(..., description="ユーザー情報")


class TokenPayload(BaseModel):
    """JWTペイロードスキーマ（内部使用）"""

    sub: str | None = Field(None, description="ユーザーID")
    exp: int | None = Field(None, description="有効期限（UNIX時間）")
    iat: int | None = Field(None, description="発行時刻（UNIX時間）")
    jti: str | None = Field(None, description="JWT ID")
    type: str | None = Field(None, description="トークンタイプ")


class RefreshTokenRequest(BaseModel):
    """リフレッシュトークンリクエストスキーマ"""

    refresh_token: str = Field(
        ..., description="リフレッシュトークン", examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )


class PasswordChangeRequest(BaseModel):
    """パスワード変更リクエストスキーマ"""

    current_password: str = Field(
        ..., min_length=1, max_length=UserConstants.PASSWORD_MAX_LENGTH, description="現在のパスワード"
    )

    new_password: str = Field(
        ...,
        min_length=UserConstants.PASSWORD_MIN_LENGTH,
        max_length=UserConstants.PASSWORD_MAX_LENGTH,
        description="新しいパスワード",
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < UserConstants.PASSWORD_MIN_LENGTH:
            raise ValueError(ErrorMessages.PASSWORD_TOO_SHORT)

        if len(v) > UserConstants.PASSWORD_MAX_LENGTH:
            raise ValueError(ErrorMessages.PASSWORD_TOO_LONG)

        if not re.search(r"[A-Za-z]", v):
            raise ValueError(ErrorMessages.PASSWORD_NO_LETTERS)

        if not re.search(r"\d", v):
            raise ValueError(ErrorMessages.PASSWORD_NO_NUMBERS)

        if is_weak_password(v):
            raise ValueError(ErrorMessages.PASSWORD_TOO_WEAK)

        return v


class AuthResponse(BaseModel):
    """汎用認証レスポンススキーマ"""

    success: bool = Field(..., description="成功フラグ")
    message: str = Field(..., description="メッセージ")
    data: dict | None = Field(None, description="追加データ")


# スキーマの使用例とドキュメント用の設定
class AuthSchemaExamples:
    """認証スキーマの使用例"""

    USER_CREATE_EXAMPLE = {"email": "user@example.com", "password": "SecurePassword123!", "display_name": "山田太郎"}

    USER_LOGIN_EXAMPLE = {"email": "user@example.com", "password": "SecurePassword123!"}

    PASSWORD_CHANGE_EXAMPLE = {"current_password": "OldPassword123!", "new_password": "NewSecurePassword456!"}
