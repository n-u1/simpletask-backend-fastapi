"""タスクリポジトリ

タスクデータアクセス層の抽象化
"""

import uuid
from abc import ABC, abstractmethod

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import Task


class TaskRepositoryInterface(ABC):
    """タスクリポジトリのインターフェース"""

    @abstractmethod
    async def get_by_id(self, db: AsyncSession, task_id: uuid.UUID) -> Task | None:
        """IDでタスクを取得"""
        pass

    @abstractmethod
    async def get_by_user(self, db: AsyncSession, user_id: uuid.UUID, task_id: uuid.UUID) -> Task | None:
        """ユーザーIDとタスクIDでタスクを取得"""
        pass

    @abstractmethod
    async def get_user_tasks(self, db: AsyncSession, user_id: uuid.UUID, skip: int = 0, limit: int = 20) -> list[Task]:
        """ユーザーのタスク一覧を取得"""
        pass


class TaskRepository(TaskRepositoryInterface):
    """タスクリポジトリの実装"""

    async def get_by_id(self, db: AsyncSession, task_id: uuid.UUID) -> Task | None:
        """IDでタスクを取得

        Args:
            db: データベースセッション
            task_id: タスクID

        Returns:
            タスクインスタンスまたはNone
        """
        from app.crud.task import task_crud

        return await task_crud.get(db, id=task_id)

    async def get_by_user(self, db: AsyncSession, user_id: uuid.UUID, task_id: uuid.UUID) -> Task | None:
        """ユーザーIDとタスクIDでタスクを取得

        Args:
            db: データベースセッション
            user_id: ユーザーID
            task_id: タスクID

        Returns:
            タスクインスタンスまたはNone
        """
        from app.crud.task import task_crud

        return await task_crud.get_by_user(db, user_id=user_id, task_id=task_id)

    async def get_user_tasks(self, db: AsyncSession, user_id: uuid.UUID, skip: int = 0, limit: int = 20) -> list[Task]:
        """ユーザーのタスク一覧を取得

        Args:
            db: データベースセッション
            user_id: ユーザーID
            skip: スキップ件数
            limit: 取得件数

        Returns:
            タスクインスタンスのリスト
        """
        from app.crud.task import task_crud

        return await task_crud.get_multi_by_user(db, user_id=user_id, skip=skip, limit=limit)

    async def get_with_tag_info(self, db: AsyncSession, task_id: uuid.UUID, user_id: uuid.UUID) -> dict | None:
        """タグ情報を含むタスクデータを取得

        Args:
            db: データベースセッション
            task_id: タスクID
            user_id: ユーザーID

        Returns:
            TaskResponse用の辞書データまたはNone
        """
        # タスクをリレーションシップ込みで取得
        from app.models.task_tag import TaskTag

        result = await db.execute(
            select(Task)
            .options(selectinload(Task.task_tags).selectinload(TaskTag.tag))
            .where(Task.id == task_id, Task.user_id == user_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            return None

        task_dict = {
            "id": task.id,
            "user_id": task.user_id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "due_date": task.due_date,
            "completed_at": task.completed_at,
            "position": task.position,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "is_completed": task.is_completed,
            "is_archived": task.is_archived,
            "is_overdue": task.is_overdue,
            "days_until_due": task.days_until_due,
            "tag_names": task.tag_names,
            # TagInfo用の基本情報のみ
            "tags": [
                {
                    "id": task_tag.tag.id,
                    "name": task_tag.tag.name,
                    "color": task_tag.tag.color,
                    "description": task_tag.tag.description,
                }
                for task_tag in task.task_tags
                if task_tag.tag
            ],
        }

        return task_dict

    async def create_with_response_data(self, task: Task) -> dict:
        """タスク作成後にレスポンス用のデータを構築

        Args:
            task: 作成されたタスクインスタンス

        Returns:
            TaskResponse用の辞書データ
        """
        # 基本データを取得
        task_dict = {
            "id": task.id,
            "user_id": task.user_id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "due_date": task.due_date,
            "completed_at": task.completed_at,
            "position": task.position,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "is_completed": task.is_completed,
            "is_archived": task.is_archived,
            "is_overdue": task.is_overdue,
            "days_until_due": task.days_until_due,
            "tag_names": [],
            "tags": [],
        }

        return task_dict

    async def get_multiple_with_tag_info(self, db: AsyncSession, tasks: list[Task]) -> list[dict]:
        """複数タスクのタグ情報を含むデータを取得

        Args:
            db: データベースセッション
            tasks: タスクリスト

        Returns:
            TaskResponse用の辞書データのリスト
        """
        if not tasks:
            return []

        task_ids = [task.id for task in tasks]

        # リレーションシップ込みで一括取得
        from app.models.task_tag import TaskTag

        result = await db.execute(
            select(Task).options(selectinload(Task.task_tags).selectinload(TaskTag.tag)).where(Task.id.in_(task_ids))
        )
        tasks_with_tags = result.scalars().all()

        # ID でマッピング
        task_map = {task.id: task for task in tasks_with_tags}

        task_dicts = []
        for task in tasks:
            task_with_tags = task_map.get(task.id, task)

            task_dict = {
                "id": task.id,
                "user_id": task.user_id,
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "due_date": task.due_date,
                "completed_at": task.completed_at,
                "position": task.position,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "is_completed": task.is_completed,
                "is_archived": task.is_archived,
                "is_overdue": task.is_overdue,
                "days_until_due": task.days_until_due,
                "tag_names": task_with_tags.tag_names if hasattr(task_with_tags, "task_tags") else [],
                # TagInfo用の基本情報のみ
                "tags": [
                    {
                        "id": task_tag.tag.id,
                        "name": task_tag.tag.name,
                        "color": task_tag.tag.color,
                        "description": task_tag.tag.description,
                    }
                    for task_tag in getattr(task_with_tags, "task_tags", [])
                    if task_tag.tag
                ],
            }
            task_dicts.append(task_dict)

        return task_dicts


# シングルトンインスタンス
task_repository = TaskRepository()
