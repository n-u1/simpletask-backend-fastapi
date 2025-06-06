"""データベース操作関連ユーティリティ

UUID変換、クエリ構築、関連データの取得など、データベース操作の共通処理を提供
"""

import contextlib
from typing import Any, Protocol, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

# SQLAlchemy モデルの型変数
ModelType = TypeVar("ModelType")


class HasTaskTags(Protocol):
    """task_tags属性を持つモデルのプロトコル"""

    task_tags: Any


class HasUserId(Protocol):
    """user_id属性を持つモデルのプロトコル"""

    user_id: Any


class HasId(Protocol):
    """id属性を持つモデルのプロトコル"""

    id: Any


class HasIsActive(Protocol):
    """is_active属性を持つモデルのプロトコル"""

    is_active: Any


class HasCreatedAt(Protocol):
    """created_at属性を持つモデルのプロトコル"""

    created_at: Any


def safe_uuid_convert(value: Any, field_name: str = "ID") -> UUID:
    """安全なUUID変換

    Args:
        value: 変換対象の値
        field_name: フィールド名（エラーメッセージ用）

    Returns:
        UUID オブジェクト

    Raises:
        ValueError: UUID変換に失敗した場合
    """
    if isinstance(value, UUID):
        return value

    if value is None:
        raise ValueError(f"{field_name}が指定されていません")

    try:
        return UUID(str(value))
    except (ValueError, TypeError) as e:
        raise ValueError(f"無効な{field_name}形式です: {value}") from e


def create_base_query(model_class: type[Any]) -> Select[tuple[Any]]:
    """ベースクエリを作成

    Args:
        model_class: SQLAlchemyモデルクラス

    Returns:
        ベースクエリオブジェクト
    """
    return select(model_class)


def create_query_with_task_tags(model_class: type[Any]) -> Select[tuple[Any]]:
    """タスクタグ情報を含むクエリを作成

    タスクモデル用の関連データ（タグ）を含むクエリを構築

    Args:
        model_class: タスクモデルクラス

    Returns:
        タグ情報を含むクエリオブジェクト
    """
    if not hasattr(model_class, "task_tags"):
        return select(model_class)

    task_tags_attr = model_class.task_tags
    tag_attr = task_tags_attr.property.mapper.class_.tag

    return select(model_class).options(selectinload(task_tags_attr).selectinload(tag_attr))


def create_query_with_tag_tasks(model_class: type[Any]) -> Select[tuple[Any]]:
    """タグタスク情報を含むクエリを作成

    タグモデル用の関連データ（タスク）を含むクエリを構築

    Args:
        model_class: タグモデルクラス

    Returns:
        タスク情報を含むクエリオブジェクト
    """
    if not hasattr(model_class, "task_tags"):
        return select(model_class)

    task_tags_attr = model_class.task_tags
    task_attr = task_tags_attr.property.mapper.class_.task

    return select(model_class).options(selectinload(task_tags_attr).selectinload(task_attr))


def add_user_filter(query: Select[tuple[Any]], model_class: type[Any], user_id: UUID) -> Select[tuple[Any]]:
    """ユーザーフィルタを追加

    Args:
        query: 既存のクエリ
        model_class: モデルクラス
        user_id: ユーザーID

    Returns:
        ユーザーフィルタが追加されたクエリ
    """
    if hasattr(model_class, "user_id"):
        return query.where(model_class.user_id == user_id)
    return query


def add_active_filter(
    query: Select[tuple[Any]], model_class: type[Any], include_inactive: bool = False
) -> Select[tuple[Any]]:
    """アクティブ状態フィルタを追加

    Args:
        query: 既存のクエリ
        model_class: モデルクラス
        include_inactive: 非アクティブも含めるかどうか

    Returns:
        アクティブ状態フィルタが追加されたクエリ
    """
    if not include_inactive and hasattr(model_class, "is_active"):
        return query.where(model_class.is_active == True)  # noqa: E712
    return query


def add_pagination(query: Select[tuple[Any]], skip: int = 0, limit: int = 100) -> Select[tuple[Any]]:
    """ページネーションを追加

    Args:
        query: 既存のクエリ
        skip: スキップする件数
        limit: 取得する最大件数

    Returns:
        ページネーションが追加されたクエリ
    """
    return query.offset(skip).limit(limit)


def add_default_ordering(query: Select[tuple[Any]], model_class: type[Any]) -> Select[tuple[Any]]:
    """デフォルトソートを追加

    Args:
        query: 既存のクエリ
        model_class: モデルクラス

    Returns:
        デフォルトソートが追加されたクエリ
    """
    if hasattr(model_class, "created_at"):
        return query.order_by(model_class.created_at.desc())
    return query


class QueryBuilder:
    """クエリビルダークラス

    複雑なクエリを段階的に構築するためのヘルパークラス
    """

    def __init__(self, model_class: type[Any]):
        self.model_class = model_class
        self.query: Select[tuple[Any]] = create_base_query(model_class)

    def with_task_tags(self) -> "QueryBuilder":
        """タスクタグ情報を含める"""
        self.query = create_query_with_task_tags(self.model_class)
        return self

    def with_tag_tasks(self) -> "QueryBuilder":
        """タグタスク情報を含める"""
        self.query = create_query_with_tag_tasks(self.model_class)
        return self

    def filter_by_user(self, user_id: UUID) -> "QueryBuilder":
        """ユーザーでフィルタ"""
        self.query = add_user_filter(self.query, self.model_class, user_id)
        return self

    def filter_active(self, include_inactive: bool = False) -> "QueryBuilder":
        """アクティブ状態でフィルタ"""
        self.query = add_active_filter(self.query, self.model_class, include_inactive)
        return self

    def paginate(self, skip: int = 0, limit: int = 100) -> "QueryBuilder":
        """ページネーション追加"""
        self.query = add_pagination(self.query, skip, limit)
        return self

    def order_by_default(self) -> "QueryBuilder":
        """デフォルトソート追加"""
        self.query = add_default_ordering(self.query, self.model_class)
        return self

    def order_by(self, *columns: Any) -> "QueryBuilder":
        """カスタムソート追加"""
        self.query = self.query.order_by(*columns)
        return self

    def where(self, *conditions: Any) -> "QueryBuilder":
        """WHERE条件追加"""
        self.query = self.query.where(*conditions)
        return self

    def build(self) -> Select[tuple[Any]]:
        """クエリを構築して返す"""
        return self.query


def create_user_resource_query(
    model_class: type[Any],
    user_id: UUID,
    target_id: UUID | None = None,
    include_inactive: bool = False,
    with_relations: bool = False,
) -> Select[tuple[Any]]:
    """ユーザーリソース用の標準クエリを作成

    Args:
        model_class: モデルクラス
        user_id: ユーザーID
        target_id: 特定のリソースID（指定した場合は単一リソース取得用）
        include_inactive: 非アクティブリソースを含めるか
        with_relations: 関連データを含めるか

    Returns:
        構築されたクエリ
    """
    builder = QueryBuilder(model_class)

    # 関連データの追加（条件を統合）
    if with_relations and hasattr(model_class, "task_tags"):
        builder.with_task_tags()

    # 基本フィルタ
    builder.filter_by_user(user_id)

    # 特定リソースの指定
    if target_id is not None and hasattr(model_class, "id"):
        builder.where(model_class.id == target_id)

    # アクティブ状態フィルタ
    builder.filter_active(include_inactive)

    # デフォルトソート（単一リソース取得時は不要）
    if target_id is None:
        builder.order_by_default()

    return builder.build()


def create_count_query(model_class: type[Any], user_id: UUID, include_inactive: bool = False) -> Select[tuple[int]]:
    """カウント用クエリを作成

    Args:
        model_class: モデルクラス
        user_id: ユーザーID
        include_inactive: 非アクティブリソースを含めるか

    Returns:
        カウント用クエリ
    """
    from sqlalchemy import func

    if not hasattr(model_class, "id"):
        raise ValueError("モデルクラスにidフィールドがありません")

    query = select(func.count(model_class.id))

    if hasattr(model_class, "user_id"):
        query = query.where(model_class.user_id == user_id)

    if not include_inactive and hasattr(model_class, "is_active"):
        query = query.where(model_class.is_active == True)  # noqa: E712

    return query


class DatabaseSessionMixin:
    """データベースセッション関連のミックスイン

    共通的なセッション操作を提供
    """

    @staticmethod
    async def safe_commit(db: Any) -> None:
        """安全なコミット処理

        Args:
            db: データベースセッション

        Raises:
            Exception: コミット失敗時
        """
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    @staticmethod
    async def safe_refresh(db: Any, obj: Any) -> None:
        """安全なリフレッシュ処理

        Args:
            db: データベースセッション
            obj: リフレッシュ対象のオブジェクト
        """
        with contextlib.suppress(Exception):
            # リフレッシュに失敗した場合は無視
            # オブジェクトが削除済みなどの場合に発生する可能性があるため
            await db.refresh(obj)


# 関数エイリアス
def build_query(model_class: type[Any]) -> QueryBuilder:
    """QueryBuilderのファクトリ関数

    Args:
        model_class: モデルクラス

    Returns:
        QueryBuilderインスタンス
    """
    return QueryBuilder(model_class)
