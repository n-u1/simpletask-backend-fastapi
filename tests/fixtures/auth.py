"""認証関連フィクスチャ"""

from typing import Any

import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def auth_headers(async_client: AsyncClient, test_user: dict[str, Any]) -> dict[str, str]:
    """認証済みユーザーのヘッダー"""
    response = await async_client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user["email"],
            "password": test_user["password"],
        },
    )
    assert response.status_code == 200
    token_data = response.json()

    return {"Authorization": f"Bearer {token_data['access_token']}"}
