"""ユーザーモデル

認証・認可、プロフィール管理機能を提供
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base

# 循環インポート回避のための型チェック時のみインポート
if TYPE_CHECKING:
    from app.models.tag import Tag  # noqa: F401
    from app.models.task import Task  # noqa: F401


class User(Base):
    """ユーザーモデル

    認証情報、プロフィール、アカウント状態を管理
    """

    # 基本認証情報
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True, comment="メールアドレス（ログインID）"
    )

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="Argon2ハッシュ化されたパスワード")

    # プロフィール情報
    display_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="表示名")

    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="アバター画像URL")

    # アカウント状態管理
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="アカウント有効フラグ")

    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="メールアドレス認証済みフラグ"
    )

    # セキュリティ関連
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最終ログイン日時")

    failed_login_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="連続ログイン失敗回数"
    )

    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="アカウントロック解除日時")

    # リレーション定義（遅延読み込み）
    tasks = relationship(
        "Task", back_populates="owner", cascade="all, delete-orphan", lazy="select", passive_deletes=True
    )

    tags = relationship(
        "Tag", back_populates="owner", cascade="all, delete-orphan", lazy="select", passive_deletes=True
    )

    # 複合インデックス定義
    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
        Index("ix_users_active_verified", "is_active", "is_verified"),
        Index("ix_users_last_login", "last_login_at"),
    )

    # バリデーション
    @validates("email")
    def validate_email(self, key: str, email: str) -> str:  # noqa: ARG002
        if not email:
            raise ValueError("メールアドレスは必須です")

        # 基本的な形式チェック（詳細はPydanticで実施）
        import re

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email.strip()):
            raise ValueError("有効なメールアドレスを入力してください")

        return email.lower().strip()

    @validates("display_name")
    def validate_display_name(self, key: str, display_name: str) -> str:  # noqa: ARG002
        if not display_name or not display_name.strip():
            raise ValueError("表示名は必須です")

        display_name = display_name.strip()

        if len(display_name) < 2:
            raise ValueError("表示名は2文字以上で入力してください")

        if len(display_name) > 100:
            raise ValueError("表示名は100文字以内で入力してください")

        return display_name

    @validates("failed_login_attempts")
    def validate_failed_attempts(self, key: str, attempts: int) -> int:  # noqa: ARG002
        return max(0, attempts)  # 負の値を防ぐ

    # ビジネスロジックメソッド
    def record_login_success(self) -> None:
        """ログイン成功を記録"""
        self.last_login_at = datetime.now(UTC)
        self.failed_login_attempts = 0
        self.locked_until = None

    def record_login_failure(self, max_attempts: int = 5, lockout_duration_minutes: int = 30) -> None:
        """ログイン失敗を記録

        Args:
            max_attempts: 最大失敗回数
            lockout_duration_minutes: ロック時間（分）
        """
        self.failed_login_attempts += 1

        if self.failed_login_attempts >= max_attempts:
            from datetime import timedelta

            self.locked_until = datetime.now(UTC) + timedelta(minutes=lockout_duration_minutes)

    @property
    def is_locked(self) -> bool:
        """アカウントがロックされているかチェック"""
        if self.locked_until is None:
            return False
        return datetime.now(UTC) < self.locked_until

    @property
    def can_login(self) -> bool:
        """ログイン可能かチェック"""
        return self.is_active and not self.is_locked

    def to_dict(self) -> dict:
        """辞書形式に変換"""
        data = super().to_dict()
        # セキュリティ上重要な情報は除外
        data.pop("password_hash", None)
        data.pop("failed_login_attempts", None)
        data.pop("locked_until", None)
        return data

    def __repr__(self) -> str:
        return f"<User(email={self.email}, display_name={self.display_name}, active={self.is_active})>"
