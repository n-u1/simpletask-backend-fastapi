"""認証関連のPydanticスキーマ

ユーザー登録、ログイン、トークンのリクエスト・レスポンススキーマを提供
"""

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """ユーザー作成（登録）リクエストスキーマ"""

    email: EmailStr = Field(..., description="メールアドレス", examples=["user@example.com"])

    password: str = Field(
        ..., min_length=8, max_length=128, description="パスワード（8文字以上）", examples=["SecurePassword123!"]
    )

    display_name: str = Field(..., min_length=2, max_length=100, description="表示名", examples=["田中太郎"])

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("パスワードは8文字以上である必要があります")

        if len(v) > 128:
            raise ValueError("パスワードは128文字以内で入力してください")

        if not re.search(r"[A-Za-z]", v):
            raise ValueError("パスワードには英字を含めてください")

        if not re.search(r"\d", v):
            raise ValueError("パスワードには数字を含めてください")

        weak_passwords = ["password", "12345678", "qwerty", "admin"]
        if v.lower() in weak_passwords:
            raise ValueError("このパスワードは簡単すぎるため使用できません")

        return v

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: str) -> str:
        v = v.strip()

        if len(v) < 2:
            raise ValueError("表示名は2文字以上で入力してください")

        if len(v) > 100:
            raise ValueError("表示名は100文字以内で入力してください")

        if not re.match(r"^[a-zA-Z0-9ぁ-んァ-ヶー一-龠\s\-_\.]+$", v):
            raise ValueError("表示名に使用できない文字が含まれています")

        return v


class UserLogin(BaseModel):
    """ログインリクエストスキーマ"""

    email: EmailStr = Field(..., description="メールアドレス", examples=["user@example.com"])

    password: str = Field(..., min_length=1, max_length=128, description="パスワード", examples=["SecurePassword123!"])


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

    current_password: str = Field(..., min_length=1, max_length=128, description="現在のパスワード")

    new_password: str = Field(..., min_length=8, max_length=128, description="新しいパスワード")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("パスワードは8文字以上である必要があります")

        if len(v) > 128:
            raise ValueError("パスワードは128文字以内で入力してください")

        if not re.search(r"[A-Za-z]", v):
            raise ValueError("パスワードには英字を含めてください")

        if not re.search(r"\d", v):
            raise ValueError("パスワードには数字を含めてください")

        weak_passwords = ["password", "12345678", "qwerty", "admin"]
        if v.lower() in weak_passwords:
            raise ValueError("このパスワードは簡単すぎるため使用できません")

        return v


class PasswordResetRequest(BaseModel):
    """パスワードリセット要求スキーマ"""

    email: EmailStr = Field(..., description="登録済みメールアドレス", examples=["user@example.com"])


class PasswordResetConfirm(BaseModel):
    """パスワードリセット確認スキーマ"""

    token: str = Field(
        ..., description="パスワードリセットトークン", examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )

    new_password: str = Field(..., min_length=8, max_length=128, description="新しいパスワード")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("パスワードは8文字以上である必要があります")

        if len(v) > 128:
            raise ValueError("パスワードは128文字以内で入力してください")

        if not re.search(r"[A-Za-z]", v):
            raise ValueError("パスワードには英字を含めてください")

        if not re.search(r"\d", v):
            raise ValueError("パスワードには数字を含めてください")

        weak_passwords = ["password", "12345678", "qwerty", "admin"]
        if v.lower() in weak_passwords:
            raise ValueError("このパスワードは簡単すぎるため使用できません")

        return v


class UserUpdate(BaseModel):
    """ユーザー情報更新スキーマ"""

    display_name: str | None = Field(None, min_length=2, max_length=100, description="表示名")

    avatar_url: str | None = Field(None, max_length=500, description="アバター画像URL")

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: str | None) -> str | None:
        if v is None:
            return v

        v = v.strip()

        if len(v) < 2:
            raise ValueError("表示名は2文字以上で入力してください")

        if len(v) > 100:
            raise ValueError("表示名は100文字以内で入力してください")

        if not re.match(r"^[a-zA-Z0-9ぁ-んァ-ヶー一-龠\s\-_\.]+$", v):
            raise ValueError("表示名に使用できない文字が含まれています")

        return v

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return None

        v = v.strip()

        url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
        if not re.match(url_pattern, v):
            raise ValueError("有効なURLを入力してください")

        valid_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        if not any(v.lower().endswith(ext) for ext in valid_extensions):
            raise ValueError("画像ファイル（jpg, jpeg, png, gif, webp）のURLを入力してください")

        return v


class AuthResponse(BaseModel):
    """汎用認証レスポンススキーマ"""

    success: bool = Field(..., description="成功フラグ")
    message: str = Field(..., description="メッセージ")
    data: dict | None = Field(None, description="追加データ")


# スキーマの使用例とドキュメント用の設定
class Config:
    """スキーマ設定例"""

    schema_extra = {
        "examples": {
            "user_create": {"email": "user@example.com", "password": "SecurePassword123!", "display_name": "田中太郎"},
            "user_login": {"email": "user@example.com", "password": "SecurePassword123!"},
            "password_change": {"current_password": "OldPassword123!", "new_password": "NewSecurePassword456!"},
        }
    }
