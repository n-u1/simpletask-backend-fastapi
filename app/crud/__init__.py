"""CRUD パッケージ

すべてのCRUD操作クラスをインポート
"""

from app.crud.base import CRUDBase
from app.crud.user import CRUDUser, user_crud

# TODO: 他のCRUDクラスは後で追加
# from app.crud.task import CRUDTask, task_crud
# from app.crud.tag import CRUDTag, tag_crud

__all__ = [
    "CRUDBase",
    "CRUDUser",
    "user_crud",
    # "CRUDTask",
    # "task_crud",
    # "CRUDTag",
    # "tag_crud"
]
