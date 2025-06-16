"""サンプルデータフィクスチャ"""

import uuid
from typing import Any

import pytest


@pytest.fixture
def sample_user_data() -> dict[str, str]:
    """サンプルユーザーデータ"""
    return {
        "email": "newuser@example.com",
        "password": "newpassword123",
        "display_name": "新規ユーザー",
    }


@pytest.fixture
def sample_task_data() -> dict[str, Any]:
    """サンプルタスクデータ"""
    unique_suffix = uuid.uuid4().hex[:8]
    return {
        "title": f"テストタスク_{unique_suffix}",
        "description": f"テスト用タスクの説明_{unique_suffix}",
        "status": "todo",
        "priority": "high",
        "tag_ids": [],
    }


@pytest.fixture
def sample_tag_data() -> dict[str, str]:
    """サンプルタグデータ"""
    unique_suffix = uuid.uuid4().hex[:8]
    return {
        "name": f"テストタグ_{unique_suffix}",
        "color": "#EF4444",
        "description": f"テスト用タグの説明_{unique_suffix}",
    }
