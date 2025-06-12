"""CRUD パッケージ

すべてのCRUD操作クラスをインポートするためのエントリーポイント
"""

from app.crud.base import CRUDBase
from app.crud.tag import CRUDTag, tag_crud
from app.crud.task import CRUDTask, task_crud
from app.crud.user import CRUDUser, user_crud

__all__ = [
    "CRUDBase",
    "CRUDUser",
    "user_crud",
    "CRUDTask",
    "task_crud",
    "CRUDTag",
    "tag_crud",
]
