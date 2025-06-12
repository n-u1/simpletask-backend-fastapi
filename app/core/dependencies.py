"""依存性注入設定モジュール

リポジトリパターンの依存性注入を管理
"""

from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.repositories.tag import TagRepositoryInterface
    from app.repositories.task import TaskRepositoryInterface
    from app.repositories.user import UserRepositoryInterface


@lru_cache
def get_user_repository() -> "UserRepositoryInterface":
    """ユーザーリポジトリの依存性注入

    lru_cacheでシングルトン化してパフォーマンスを最適化

    Returns:
        ユーザーリポジトリインスタンス
    """
    from app.repositories.user import user_repository

    return user_repository


@lru_cache
def get_task_repository() -> "TaskRepositoryInterface":
    """タスクリポジトリの依存性注入

    Returns:
        タスクリポジトリインスタンス
    """
    from app.repositories.task import task_repository

    return task_repository


@lru_cache
def get_tag_repository() -> "TagRepositoryInterface":
    """タグリポジトリの依存性注入

    Returns:
        タグリポジトリインスタンス
    """
    from app.repositories.tag import tag_repository

    return tag_repository


# テスト用のリセット関数
def reset_repository_cache() -> None:
    """リポジトリキャッシュをリセット（主にテスト用）

    テスト時にモックリポジトリを注入する場合に使用
    """
    get_user_repository.cache_clear()
    get_task_repository.cache_clear()
    get_tag_repository.cache_clear()
