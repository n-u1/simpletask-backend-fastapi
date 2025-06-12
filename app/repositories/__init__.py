"""リポジトリパッケージ

データアクセス層の抽象化を提供
CRUDをカプセル化し、ビジネスロジックとの分離を実現
"""

from app.repositories.tag import TagRepository, TagRepositoryInterface, tag_repository
from app.repositories.task import TaskRepository, TaskRepositoryInterface, task_repository
from app.repositories.user import UserRepository, UserRepositoryInterface, user_repository

__all__ = [
    # Interfaces
    "UserRepositoryInterface",
    "TaskRepositoryInterface",
    "TagRepositoryInterface",
    # Implementations
    "UserRepository",
    "TaskRepository",
    "TagRepository",
    # Instances
    "user_repository",
    "task_repository",
    "tag_repository",
]
