"""タグモデル

タスクの分類・整理用のタグ機能を提供
"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.constants import ErrorMessages, TagConstants, validate_color_code
from app.models.base import Base

# 循環インポート回避のための型チェック時のみインポート
if TYPE_CHECKING:
    from app.models.task_tag import TaskTag  # noqa: F401
    from app.models.user import User  # noqa: F401


class Tag(Base):
    """タグモデル

    タスクの分類・整理機能を提供
    - カラーコード管理
    - ユーザー単位でのタグ名の一意性確保
    - タスクとの多対多関係
    """

    # 所有者（外部キー）
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="タグの所有者ID"
    )

    # 基本情報
    name: Mapped[str] = mapped_column(String(TagConstants.NAME_MAX_LENGTH), nullable=False, comment="タグ名")

    color: Mapped[str] = mapped_column(
        String(7),  # #RRGGBB形式
        nullable=False,
        default=TagConstants.DEFAULT_COLOR,
        comment="タグの表示色（16進数カラーコード）",
    )

    description: Mapped[str | None] = mapped_column(
        String(TagConstants.DESCRIPTION_MAX_LENGTH), nullable=True, comment="タグの説明"
    )

    # ステータス管理
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="アクティブフラグ（ソフトデリート用）"
    )

    # リレーション定義
    owner: Mapped["User"] = relationship("User", back_populates="tags", lazy="select")

    task_tags: Mapped[list["TaskTag"]] = relationship(
        "TaskTag", back_populates="tag", cascade="all, delete-orphan", lazy="select", passive_deletes=True
    )

    # 制約・インデックス定義
    __table_args__ = (
        # ユニーク制約: 同一ユーザー内でアクティブなタグ名は重複不可
        UniqueConstraint("user_id", "name", name="uq_tags_user_name"),
        # 複合インデックス
        Index("ix_tags_user_name", "user_id", "name"),
        Index("ix_tags_user_active", "user_id", "is_active"),
        Index("ix_tags_active", "is_active"),
    )

    @validates("name")
    def validate_name(self, key: str, name: str) -> str:  # noqa: ARG002
        if not name or not name.strip():
            raise ValueError(ErrorMessages.TAG_NAME_REQUIRED)

        name = name.strip()

        if len(name) < TagConstants.NAME_MIN_LENGTH:
            raise ValueError(ErrorMessages.TAG_NAME_REQUIRED)

        if len(name) > TagConstants.NAME_MAX_LENGTH:
            raise ValueError(ErrorMessages.TAG_NAME_TOO_LONG)

        return name

    @validates("color")
    def validate_color(self, key: str, color: str) -> str:  # noqa: ARG002
        if not color:
            return TagConstants.DEFAULT_COLOR

        color = color.strip().upper()

        if not validate_color_code(color):
            raise ValueError(ErrorMessages.TAG_COLOR_INVALID)

        return color

    @validates("description")
    def validate_description(self, key: str, description: str | None) -> str | None:  # noqa: ARG002
        if description is None:
            return None

        description = description.strip()

        if len(description) > TagConstants.DESCRIPTION_MAX_LENGTH:
            raise ValueError(f"タグ説明は{TagConstants.DESCRIPTION_MAX_LENGTH}文字以内で入力してください")

        return description if description else None

    @property
    def tasks(self) -> list:
        """関連するタスクのリスト"""
        return [task_tag.task for task_tag in self.task_tags if task_tag.task]

    @property
    def task_count(self) -> int:
        """関連するタスク数"""
        return len([task_tag for task_tag in self.task_tags if task_tag.task])

    @property
    def active_task_count(self) -> int:
        """関連するアクティブなタスク数（アーカイブ済みを除く）"""
        return len([task_tag for task_tag in self.task_tags if task_tag.task and task_tag.task.status != "archived"])

    @property
    def completed_task_count(self) -> int:
        """関連する完了済みタスク数"""
        return len([task_tag for task_tag in self.task_tags if task_tag.task and task_tag.task.status == "done"])

    @property
    def color_rgb(self) -> tuple[int, int, int]:
        """カラーコードをRGBタプルに変換"""
        color = self.color.lstrip("#")
        rgb_values = tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))
        # MyPy対応: 明示的に3要素のタプルであることを保証
        return (rgb_values[0], rgb_values[1], rgb_values[2])

    @property
    def is_preset_color(self) -> bool:
        """プリセットカラーかどうか"""
        return self.color in TagConstants.PRESET_COLORS

    def to_dict(self) -> dict:
        """辞書形式に変換（API応答用）"""
        data = super().to_dict()

        # 追加の計算プロパティを含める
        data.update(
            {
                "task_count": self.task_count,
                "active_task_count": self.active_task_count,
                "completed_task_count": self.completed_task_count,
                "color_rgb": self.color_rgb,
                "is_preset_color": self.is_preset_color,
            }
        )

        return data

    def __repr__(self) -> str:
        return f"<Tag(name={self.name}, color={self.color}, active={self.is_active})>"
