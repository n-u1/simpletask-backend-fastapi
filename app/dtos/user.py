"""ユーザーDTO

ユーザーデータの転送オブジェクト
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.dtos.base import BaseDTO


@dataclass(frozen=True)
class UserSummaryDTO:
    """ユーザー要約DTO（他のエンティティから参照される簡略版）

    他の機能でユーザー情報を参照する際に使用する軽量版
    """

    id: UUID
    display_name: str
    avatar_url: str | None = None


@dataclass(frozen=True)
class UserDTO(BaseDTO):
    """ユーザーDTO（完全版）

    ユーザーの完全な情報を含むDTO
    セキュリティ上重要な情報は除外
    """

    email: str
    display_name: str
    avatar_url: str | None
    is_active: bool
    is_verified: bool
    last_login_at: datetime | None

    # 認証で必要な追加情報
    locked_until: datetime | None = None

    @property
    def initials(self) -> str:
        """表示名からイニシャルを生成（アバター代替表示用）"""
        if not self.display_name:
            return "?"

        words = self.display_name.strip().split()
        if len(words) >= 2:
            return f"{words[0][0]}{words[1][0]}".upper()
        elif len(words) == 1:
            return words[0][0].upper()
        else:
            return "?"

    @property
    def is_profile_complete(self) -> bool:
        """プロフィールが完全かどうか"""
        return bool(self.display_name and self.is_verified)

    @property
    def is_locked(self) -> bool:
        """アカウントがロックされているかチェック"""
        if self.locked_until is None:
            return False
        from datetime import UTC

        return datetime.now(UTC) < self.locked_until

    @property
    def can_login(self) -> bool:
        """ログイン可能かチェック"""
        return self.is_active and not self.is_locked


@dataclass(frozen=True)
class UserProfileDTO:
    """ユーザープロフィールDTO（更新可能フィールドのみ）

    プロフィール更新で使用される情報
    """

    display_name: str
    avatar_url: str | None
