"""タスクDTO

タスクデータの転送オブジェクト
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.dtos.base import BaseDTO
from app.dtos.tag import TagSummaryDTO


@dataclass(frozen=True)
class TaskDTO(BaseDTO):
    """タスクDTO（完全版）

    タスクの完全な情報とタグ関係を含むDTO
    """

    user_id: UUID
    title: str
    description: str | None
    status: str
    priority: str
    due_date: datetime | None
    completed_at: datetime | None
    position: int

    # 関連タグ情報
    tags: list[TagSummaryDTO]

    @property
    def is_completed(self) -> bool:
        """完了済みかどうか"""
        return self.status == "done"

    @property
    def is_archived(self) -> bool:
        """アーカイブ済みかどうか"""
        return self.status == "archived"

    @property
    def is_overdue(self) -> bool:
        """期限切れかどうか（完了済みタスクは期限切れ扱いしない）"""
        if not self.due_date or self.is_completed:
            return False
        return self.due_date < datetime.now(UTC)

    @property
    def days_until_due(self) -> int | None:
        """期限までの日数（期限なしの場合はNone、過ぎている場合は負の値）"""
        if not self.due_date:
            return None

        delta = self.due_date.date() - datetime.now(UTC).date()
        return delta.days

    @property
    def tag_names(self) -> list[str]:
        """関連するタグ名のリスト"""
        return [tag.name for tag in self.tags]


@dataclass(frozen=True)
class TaskListDTO:
    """タスク一覧DTO

    ページネーション情報とタスクリストを含む
    """

    tasks: list[TaskDTO]
    total: int
    page: int
    per_page: int
    total_pages: int
