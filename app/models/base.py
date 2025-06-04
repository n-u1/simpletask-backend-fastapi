"""SQLAlchemyベースモデル

すべてのモデルの基底クラスを提供
UUIDプライマリキー、タイムスタンプ、ネーミング規則を統一
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, MetaData
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# PostgreSQL制約命名規則の統一
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",  # インデックス
        "uq": "uq_%(table_name)s_%(column_0_name)s",  # ユニーク制約
        "ck": "ck_%(table_name)s_%(constraint_name)s",  # チェック制約
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",  # 外部キー
        "pk": "pk_%(table_name)s",  # プライマリキー
    }
)


class Base(DeclarativeBase):
    """SQLAlchemy 2.x準拠のベースクラス

    全てのモデルはこのクラスを継承する
    - UUID主キー
    - 作成・更新タイムスタンプ
    - テーブル名自動生成
    """

    metadata = metadata

    # 型注釈（SQLAlchemy 2.x）
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True, comment="プライマリキー（UUID）"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False, comment="作成日時（UTC）"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
        comment="更新日時（UTC）",
    )

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """テーブル名を自動生成

        例: User -> users, TaskTag -> task_tags
        """
        import re

        name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", cls.__name__)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower() + "s"

    def __repr__(self) -> str:
        """デバッグ用の文字列表現"""
        return f"<{self.__class__.__name__}(id={self.id})>"

    def to_dict(self) -> dict[str, Any]:
        """モデルを辞書形式に変換（シリアライゼーション用）

        注意: パスワードハッシュなど機密情報は除外する必要がある
        """
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}
