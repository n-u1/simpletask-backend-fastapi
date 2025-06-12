"""タスクモデル

タスクの作成、管理、ステータス変更機能を提供
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.constants import ErrorMessages, TaskConstants, TaskPriority, TaskStatus
from app.models.base import Base

# 循環インポート回避のための型チェック時
if TYPE_CHECKING:
    from app.models.task_tag import TaskTag  # noqa: F401
    from app.models.user import User  # noqa: F401


class Task(Base):
    """タスクモデル

    ユーザーのタスク管理機能を提供
    - ステータス管理（TODO, IN_PROGRESS, DONE, ARCHIVED）
    - 優先度管理（LOW, MEDIUM, HIGH, URGENT）
    - 期限管理
    - 位置管理（カンバンボード用）
    """

    # 所有者（外部キー）
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="タスクの所有者ID"
    )

    title: Mapped[str] = mapped_column(String(TaskConstants.TITLE_MAX_LENGTH), nullable=False, comment="タスクタイトル")

    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="タスクの詳細説明")

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TaskConstants.DEFAULT_STATUS,
        comment="タスクステータス（todo, in_progress, done, archived）",
    )

    priority: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default=TaskConstants.DEFAULT_PRIORITY,
        comment="タスク優先度（low, medium, high, urgent）",
    )

    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="タスクの期限日時（UTC）"
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="タスク完了日時（UTC）"
    )

    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=TaskConstants.DEFAULT_POSITION, comment="表示順序（小さい値ほど上位）"
    )

    owner: Mapped["User"] = relationship("User", back_populates="tasks", lazy="select")

    task_tags: Mapped[list["TaskTag"]] = relationship(
        "TaskTag", back_populates="task", cascade="all, delete-orphan", lazy="select", passive_deletes=True
    )

    __table_args__ = (
        Index("ix_tasks_user_status", "user_id", "status"),
        Index("ix_tasks_user_priority", "user_id", "priority"),
        Index("ix_tasks_user_due_date", "user_id", "due_date"),
        Index("ix_tasks_position", "user_id", "status", "position"),
        Index("ix_tasks_completed_at", "completed_at"),
        Index("ix_tasks_created_at", "created_at"),
    )

    @validates("title")
    def validate_title(self, key: str, title: str) -> str:  # noqa: ARG002
        if not title or not title.strip():
            raise ValueError(ErrorMessages.TASK_TITLE_REQUIRED)

        title = title.strip()

        if len(title) < TaskConstants.TITLE_MIN_LENGTH:
            raise ValueError(ErrorMessages.TASK_TITLE_REQUIRED)

        if len(title) > TaskConstants.TITLE_MAX_LENGTH:
            raise ValueError(ErrorMessages.TASK_TITLE_TOO_LONG)

        return title

    @validates("status")
    def validate_status(self, key: str, status: str) -> str:  # noqa: ARG002
        if status not in [s.value for s in TaskStatus]:
            valid_statuses = ", ".join([s.value for s in TaskStatus])
            raise ValueError(f"ステータスは次のいずれかである必要があります: {valid_statuses}")
        return status

    @validates("priority")
    def validate_priority(self, key: str, priority: str) -> str:  # noqa: ARG002
        if priority not in [p.value for p in TaskPriority]:
            valid_priorities = ", ".join([p.value for p in TaskPriority])
            raise ValueError(f"優先度は次のいずれかである必要があります: {valid_priorities}")
        return priority

    @validates("position")
    def validate_position(self, key: str, position: int) -> int:  # noqa: ARG002
        if position < TaskConstants.POSITION_MIN:
            return TaskConstants.POSITION_MIN
        if position > TaskConstants.POSITION_MAX:
            return TaskConstants.POSITION_MAX
        return position

    def mark_completed(self) -> None:
        """タスクを完了状態にマーク"""
        self.status = TaskStatus.DONE.value
        self.completed_at = datetime.now(UTC)

    def mark_uncompleted(self) -> None:
        """タスクを未完了状態にマーク"""
        if self.status == TaskStatus.DONE.value:
            self.status = TaskStatus.TODO.value
        self.completed_at = None

    def archive(self) -> None:
        """タスクをアーカイブ"""
        self.status = TaskStatus.ARCHIVED.value

    def unarchive(self) -> None:
        """タスクのアーカイブを解除"""
        if self.status == TaskStatus.ARCHIVED.value:
            self.status = TaskStatus.TODO.value

    @property
    def is_completed(self) -> bool:
        """完了済みかどうか"""
        return self.status == TaskStatus.DONE.value

    @property
    def is_archived(self) -> bool:
        """アーカイブ済みかどうか"""
        return self.status == TaskStatus.ARCHIVED.value

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
    def tags(self) -> list:
        """関連するタグのリスト"""
        return [task_tag.tag for task_tag in self.task_tags if task_tag.tag]

    @property
    def tag_names(self) -> list[str]:
        """関連するタグ名のリスト"""
        return [tag.name for tag in self.tags]

    @classmethod
    def get_status_enum(cls, status_str: str) -> TaskStatus | None:
        """文字列からTaskStatusエニューを取得"""
        try:
            return TaskStatus(status_str)
        except ValueError:
            return None

    @classmethod
    def get_priority_enum(cls, priority_str: str) -> TaskPriority | None:
        """文字列からTaskPriorityエニューを取得"""
        try:
            return TaskPriority(priority_str)
        except ValueError:
            return None

    @classmethod
    def get_valid_statuses(cls) -> list[str]:
        """有効なステータス一覧を取得"""
        return [status.value for status in TaskStatus]

    @classmethod
    def get_valid_priorities(cls) -> list[str]:
        """有効な優先度一覧を取得"""
        return [priority.value for priority in TaskPriority]

    def to_dict(self) -> dict:
        """辞書形式に変換（API応答用）"""
        data = super().to_dict()

        # 追加の計算プロパティを含める
        data.update(
            {
                "is_completed": self.is_completed,
                "is_archived": self.is_archived,
                "is_overdue": self.is_overdue,
                "days_until_due": self.days_until_due,
                "tag_names": self.tag_names,
            }
        )

        return data

    def __repr__(self) -> str:
        return f"<Task(title={self.title}, status={self.status}, priority={self.priority})>"
