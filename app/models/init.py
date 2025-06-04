"""モデルパッケージ

すべてのSQLAlchemyモデルをインポート
Alembicの自動検出のため、すべてのモデルをここでインポートする必要がある
"""

from app.models.base import Base
from app.models.user import User

# TODO: 他のモデルは後で追加
# from app.models.task import Task, TaskStatus, TaskPriority
# from app.models.tag import Tag
# from app.models.task_tag import TaskTag

__all__ = [
    "Base",
    "User",
    # "Task",
    # "TaskStatus",
    # "TaskPriority",
    # "Tag",
    # "TaskTag"
]
