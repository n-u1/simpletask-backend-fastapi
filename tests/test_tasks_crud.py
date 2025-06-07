"""タスクCRUD基本動作テスト

タスクの作成・取得・更新・削除とユーザー固有データのアクセス制御テスト
"""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestTaskCreate:
    """タスク作成テスト"""

    @pytest.mark.asyncio
    async def test_create_task_success(
        self, async_client: AsyncClient, auth_headers: dict[str, str], sample_task_data: dict[str, Any]
    ) -> None:
        """正常なタスク作成"""
        response = await async_client.post("/api/v1/tasks/", headers=auth_headers, json=sample_task_data)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == sample_task_data["title"]
        assert data["description"] == sample_task_data["description"]
        assert data["status"] == sample_task_data["status"]
        assert data["priority"] == sample_task_data["priority"]
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_task_without_auth(self, async_client: AsyncClient, sample_task_data: dict[str, Any]) -> None:
        """認証なしでのタスク作成エラー"""
        response = await async_client.post("/api/v1/tasks/", json=sample_task_data)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_task_invalid_title(
        self, async_client: AsyncClient, auth_headers: dict[str, str], sample_task_data: dict[str, Any]
    ) -> None:
        """無効なタイトルでのタスク作成エラー"""
        sample_task_data["title"] = ""  # 空のタイトル

        response = await async_client.post("/api/v1/tasks/", headers=auth_headers, json=sample_task_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_task_invalid_status(
        self, async_client: AsyncClient, auth_headers: dict[str, str], sample_task_data: dict[str, Any]
    ) -> None:
        """無効なステータスでのタスク作成エラー"""
        sample_task_data["status"] = "invalid_status"

        response = await async_client.post("/api/v1/tasks/", headers=auth_headers, json=sample_task_data)

        assert response.status_code == 422


class TestTaskRead:
    """タスク取得テスト"""

    @pytest.mark.asyncio
    async def test_get_tasks_success(
        self, async_client: AsyncClient, auth_headers: dict[str, str], test_task: dict[str, Any]
    ) -> None:
        """タスク一覧取得成功"""
        response = await async_client.get("/api/v1/tasks/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert "total" in data
        assert len(data["tasks"]) >= 1

        task_ids = [task["id"] for task in data["tasks"]]
        assert str(test_task["id"]) in task_ids

    @pytest.mark.asyncio
    async def test_get_task_by_id_success(
        self, async_client: AsyncClient, auth_headers: dict[str, str], test_task: dict[str, Any]
    ) -> None:
        """特定タスク取得成功"""
        response = await async_client.get(f"/api/v1/tasks/{test_task['id']}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_task["id"])
        assert data["title"] == test_task["task"].title

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
        """存在しないタスク取得エラー"""
        from uuid import uuid4

        fake_id = uuid4()

        response = await async_client.get(f"/api/v1/tasks/{fake_id}", headers=auth_headers)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_tasks_without_auth(self, async_client: AsyncClient) -> None:
        """認証なしでのタスク取得エラー"""
        response = await async_client.get("/api/v1/tasks/")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_tasks_pagination(self, async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
        """タスク一覧のページネーション"""
        response = await async_client.get("/api/v1/tasks/?page=1&per_page=5", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 5


class TestTaskUpdate:
    """タスク更新テスト"""

    @pytest.mark.asyncio
    async def test_update_task_success(
        self, async_client: AsyncClient, auth_headers: dict[str, str], test_task: dict[str, Any]
    ) -> None:
        """タスク更新成功"""
        update_data = {
            "title": "更新されたタスク",
            "status": "in_progress",
            "priority": "high",
        }

        response = await async_client.put(f"/api/v1/tasks/{test_task['id']}", headers=auth_headers, json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["status"] == update_data["status"]
        assert data["priority"] == update_data["priority"]

    @pytest.mark.asyncio
    async def test_update_task_status_only(
        self, async_client: AsyncClient, auth_headers: dict[str, str], test_task: dict[str, Any]
    ) -> None:
        """タスクステータスのみ更新"""
        response = await async_client.patch(
            f"/api/v1/tasks/{test_task['id']}/status",
            headers=auth_headers,
            json={"status": "done"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "done"
        assert "completed_at" in data

    @pytest.mark.asyncio
    async def test_update_task_not_found(self, async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
        """存在しないタスク更新エラー"""
        from uuid import uuid4

        fake_id = uuid4()

        response = await async_client.put(
            f"/api/v1/tasks/{fake_id}",
            headers=auth_headers,
            json={"title": "更新タスク"},
        )

        assert response.status_code in [400, 403, 404]

    @pytest.mark.asyncio
    async def test_update_task_without_auth(self, async_client: AsyncClient, test_task: dict[str, Any]) -> None:
        """認証なしでのタスク更新エラー"""
        response = await async_client.put(
            f"/api/v1/tasks/{test_task['id']}",
            json={"title": "更新タスク"},
        )

        assert response.status_code == 401


class TestTaskDelete:
    """タスク削除テスト"""

    @pytest.mark.asyncio
    async def test_delete_task_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        db_session: AsyncSession,
        test_user: dict[str, Any],
    ) -> None:
        """タスク削除成功"""
        # 削除用のタスクを作成
        from app.models.task import Task

        task_data = {
            "title": "削除予定タスク",
            "description": "削除テスト用",
            "status": "todo",
            "priority": "low",
            "user_id": test_user["id"],
            "position": 0,
        }

        task = Task(**task_data)
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        # タスク削除
        response = await async_client.delete(f"/api/v1/tasks/{task.id}", headers=auth_headers)

        assert response.status_code == 204

        # 削除確認
        get_response = await async_client.get(f"/api/v1/tasks/{task.id}", headers=auth_headers)
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_task_not_found(self, async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
        """存在しないタスク削除エラー"""
        from uuid import uuid4

        fake_id = uuid4()

        response = await async_client.delete(f"/api/v1/tasks/{fake_id}", headers=auth_headers)

        assert response.status_code in [400, 403, 404]

    @pytest.mark.asyncio
    async def test_delete_task_without_auth(self, async_client: AsyncClient, test_task: dict[str, Any]) -> None:
        """認証なしでのタスク削除エラー"""
        response = await async_client.delete(f"/api/v1/tasks/{test_task['id']}")

        assert response.status_code == 401


class TestTaskAccessControl:
    """タスクアクセス制御テスト"""

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_user_task(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        sample_user_data: dict[str, str],
        test_task: dict[str, Any],
    ) -> None:
        """他のユーザーのタスクにアクセスできないことを確認"""
        # 別のユーザーを作成
        from app.core.security import security_manager
        from app.models.user import User

        other_user_data = {
            "email": "otheruser@example.com",
            "display_name": "別のユーザー",
            "password_hash": security_manager.get_password_hash("password123"),
            "is_active": True,
        }

        other_user = User(**other_user_data)
        db_session.add(other_user)
        await db_session.commit()

        # 別のユーザーでログイン
        login_response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": "otheruser@example.com",
                "password": "password123",
            },
        )
        other_user_token = login_response.json()["access_token"]
        other_user_headers = {"Authorization": f"Bearer {other_user_token}"}

        # 他のユーザーのタスクへアクセス試行
        response = await async_client.get(f"/api/v1/tasks/{test_task['id']}", headers=other_user_headers)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_can_only_see_own_tasks(
        self, async_client: AsyncClient, db_session: AsyncSession, test_task: dict[str, Any]
    ) -> None:
        """ユーザーは自分のタスクのみ表示されることを確認"""
        # 別のユーザーを作成
        from app.core.security import security_manager
        from app.models.task import Task
        from app.models.user import User

        other_user_data = {
            "email": "otheruser2@example.com",
            "display_name": "別のユーザー2",
            "password_hash": security_manager.get_password_hash("password123"),
            "is_active": True,
        }

        other_user = User(**other_user_data)
        db_session.add(other_user)
        await db_session.flush()

        # 別のユーザーのタスクを作成
        other_task_data = {
            "title": "他のユーザーのタスク",
            "description": "アクセスできないはず",
            "status": "todo",
            "priority": "medium",
            "user_id": other_user.id,
            "position": 0,
        }

        other_task = Task(**other_task_data)
        db_session.add(other_task)
        await db_session.commit()

        # 元のユーザーでログイン
        from app.models.user import User as UserModel

        original_user = await db_session.get(UserModel, test_task["task"].user_id)

        assert original_user is not None, "テストユーザーが見つかりません"

        login_response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": original_user.email,
                "password": "testpassword123",  # test_userフィクスチャのパスワード
            },
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # タスク一覧取得
        response = await async_client.get("/api/v1/tasks/", headers=headers)

        assert response.status_code == 200
        data = response.json()

        # 自分のタスクのみ表示されることを確認
        task_titles = [task["title"] for task in data["tasks"]]
        assert test_task["task"].title in task_titles
        assert "他のユーザーのタスク" not in task_titles
