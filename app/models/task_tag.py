"""タスク-タグ中間テーブルモデル

タスクとタグの多対多関係を管理
"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

# 循環インポート回避のための型チェック時
if TYPE_CHECKING:
    from app.models.tag import Tag  # noqa: F401
    from app.models.task import Task  # noqa: F401


class TaskTag(Base):
    """タスク-タグ中間テーブルモデル

    タスクとタグの多対多関係を管理
    - タスクとタグの関連付け
    - 重複関連の防止
    - カスケード削除対応
    """

    # 外部キー
    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, comment="関連付けるタスクID"
    )

    tag_id: Mapped[UUID] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), nullable=False, comment="関連付けるタグID"
    )

    # リレーション定義（Repository パターンでeager loading管理するため、デフォルトは遅延読み込み）
    task: Mapped["Task"] = relationship("Task", back_populates="task_tags", lazy="select")

    tag: Mapped["Tag"] = relationship("Tag", back_populates="task_tags", lazy="select")

    __table_args__ = (
        UniqueConstraint("task_id", "tag_id", name="uq_task_tags_task_tag"),
        Index("ix_task_tags_task_id", "task_id"),
        Index("ix_task_tags_tag_id", "tag_id"),
        Index("ix_task_tags_task_tag", "task_id", "tag_id"),
    )

    @classmethod
    def create_association(cls, task_id: UUID, tag_id: UUID) -> "TaskTag":
        """タスクとタグの関連付けを作成

        Args:
            task_id: タスクID
            tag_id: タグID

        Returns:
            TaskTagインスタンス
        """
        return cls(task_id=task_id, tag_id=tag_id)

    def get_task_title(self) -> str | None:
        """関連タスクのタイトルを取得

        注意: このメソッドは遅延読み込みを引き起こす可能性があります。
        Repository パターンで事前読み込みされた場合のみ安全に使用してください。
        """
        return self.task.title if self.task else None

    def get_tag_name(self) -> str | None:
        """関連タグの名前を取得

        注意: このメソッドは遅延読み込みを引き起こす可能性があります。
        Repository パターンで事前読み込みされた場合のみ安全に使用してください。
        """
        return self.tag.name if self.tag else None

    def get_tag_color(self) -> str | None:
        """関連タグの色を取得

        注意: このメソッドは遅延読み込みを引き起こす可能性があります。
        Repository パターンで事前読み込みされた場合のみ安全に使用してください。
        """
        return self.tag.color if self.tag else None

    def is_task_completed(self) -> bool:
        """関連タスクが完了済みかチェック

        注意: このメソッドは遅延読み込みを引き起こす可能性があります。
        Repository パターンで事前読み込みされた場合のみ安全に使用してください。
        """
        return self.task.status == "done" if self.task else False

    def is_task_archived(self) -> bool:
        """関連タスクがアーカイブ済みかチェック

        注意: このメソッドは遅延読み込みを引き起こす可能性があります。
        Repository パターンで事前読み込みされた場合のみ安全に使用してください。
        """
        return self.task.status == "archived" if self.task else False

    def is_tag_active(self) -> bool:
        """関連タグがアクティブかチェック

        注意: このメソッドは遅延読み込みを引き起こす可能性があります。
        Repository パターンで事前読み込みされた場合のみ安全に使用してください。
        """
        return self.tag.is_active if self.tag else False

    @property
    def task_status(self) -> str | None:
        """関連タスクのステータス

        注意: このプロパティは遅延読み込みを引き起こす可能性があります。
        Repository パターンで事前読み込みされた場合のみ安全に使用してください。
        """
        return self.task.status if self.task else None

    @property
    def task_priority(self) -> str | None:
        """関連タスクの優先度

        注意: このプロパティは遅延読み込みを引き起こす可能性があります。
        Repository パターンで事前読み込みされた場合のみ安全に使用してください。
        """
        return self.task.priority if self.task else None

    @property
    def tag_display_info(self) -> dict[str, str | None]:
        """タグの表示用情報

        注意: このプロパティは遅延読み込みを引き起こす可能性があります。
        Repository パターンで事前読み込みされた場合のみ安全に使用してください。
        """
        if not self.tag:
            return {"name": None, "color": None}

        return {"name": self.tag.name, "color": self.tag.color}

    @property
    def task_display_info(self) -> dict[str, str | None]:
        """タスクの表示用情報

        注意: このプロパティは遅延読み込みを引き起こす可能性があります。
        Repository パターンで事前読み込みされた場合のみ安全に使用してください。
        """
        if not self.task:
            return {"title": None, "status": None, "priority": None}

        return {"title": self.task.title, "status": self.task.status, "priority": self.task.priority}

    @classmethod
    def get_association_key(cls, task_id: UUID, tag_id: UUID) -> str:
        """タスク-タグ関連付けの一意キーを生成（キャッシュ用など）"""
        return f"task:{task_id}:tag:{tag_id}"

    def to_dict(self) -> dict:
        """辞書形式に変換（API応答用）

        注意: このメソッドは遅延読み込みを引き起こす可能性があります。
        Repository パターンで事前読み込みされた場合のみ安全に使用してください。
        """
        data = super().to_dict()

        # 関連情報を含める
        data.update(
            {
                "task_info": self.task_display_info,
                "tag_info": self.tag_display_info,
                "is_task_completed": self.is_task_completed(),
                "is_task_archived": self.is_task_archived(),
                "is_tag_active": self.is_tag_active(),
            }
        )

        return data

    def __repr__(self) -> str:
        task_title = self.get_task_title() or "Unknown"
        tag_name = self.get_tag_name() or "Unknown"
        return f"<TaskTag(task='{task_title}', tag='{tag_name}')>"
