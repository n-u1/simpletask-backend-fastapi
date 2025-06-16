"""テストエンティティフィクスチャ"""

from typing import Any

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> dict[str, Any]:
    """テスト用ユーザー作成"""
    from app.core.security import security_manager
    from app.models.user import User

    user_data = {
        "email": "test@example.com",
        "display_name": "テストユーザー",
        "password_hash": security_manager.get_password_hash("testpassword123"),
        "is_active": True,
        "is_verified": True,
    }

    user = User(**user_data)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return {
        "user": user,
        "email": user_data["email"],
        "password": "testpassword123",
        "id": user.id,
    }


@pytest_asyncio.fixture
async def test_task(db_session: AsyncSession, test_user: dict[str, Any]) -> dict[str, Any]:
    """テスト用タスク作成"""
    from app.models.task import Task

    task_data = {
        "title": "テストタスク",
        "description": "テスト用のタスクです",
        "status": "todo",
        "priority": "medium",
        "user_id": test_user["id"],
        "position": 0,
    }

    task = Task(**task_data)
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    return {"task": task, "id": task.id}


@pytest_asyncio.fixture
async def test_tag(db_session: AsyncSession, test_user: dict[str, Any]) -> dict[str, Any]:
    """テスト用タグ作成"""
    from app.models.tag import Tag

    tag_data = {
        "name": "テストタグ",
        "color": "#3B82F6",
        "description": "テスト用のタグです",
        "user_id": test_user["id"],
        "is_active": True,
    }

    tag = Tag(**tag_data)
    db_session.add(tag)
    await db_session.commit()
    await db_session.refresh(tag)

    return {"tag": tag, "id": tag.id}
