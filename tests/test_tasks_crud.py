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


class TestTaskReorder:
    """タスク並び替えテスト"""

    @pytest.mark.asyncio
    async def test_reorder_task_same_status_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        db_session: AsyncSession,
        test_user: dict[str, Any],
    ) -> None:
        """同一ステータス内でのタスク並び替え成功"""
        # 複数のタスクを作成（同じステータス）
        from app.models.task import Task

        tasks = []
        for i in range(4):
            task_data = {
                "title": f"タスク{i}",
                "description": f"テスト用タスク{i}",
                "status": "todo",
                "priority": "medium",
                "user_id": test_user["id"],
                "position": i,
            }
            task = Task(**task_data)
            db_session.add(task)
            tasks.append(task)

        await db_session.commit()
        for task in tasks:
            await db_session.refresh(task)

        # タスク1を位置3に移動（0→3）
        reorder_data = {
            "task_id": str(tasks[1].id),
            "new_position": 3,
            "new_status": None,  # 同一ステータス内移動
        }

        response = await async_client.patch("/api/v1/tasks/reorder", headers=auth_headers, json=reorder_data)

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "tasks" in data

        # 位置が正しく調整されているか確認
        updated_tasks = {task["id"]: task for task in data["tasks"]}

        # 移動したタスクの位置確認
        assert updated_tasks[str(tasks[1].id)]["position"] == 3

        # 他のタスクの位置調整確認
        assert updated_tasks[str(tasks[0].id)]["position"] == 0  # 変化なし
        assert updated_tasks[str(tasks[2].id)]["position"] == 1  # 1つ前に
        assert updated_tasks[str(tasks[3].id)]["position"] == 2  # 1つ前に

    @pytest.mark.asyncio
    async def test_reorder_task_different_status_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        db_session: AsyncSession,
        test_user: dict[str, Any],
    ) -> None:
        """異なるステータス間でのタスク移動成功"""
        from app.models.task import Task

        # TODO状態のタスクを作成
        todo_tasks = []
        for i in range(3):
            task_data = {
                "title": f"TODOタスク{i}",
                "status": "todo",
                "priority": "medium",
                "user_id": test_user["id"],
                "position": i,
            }
            task = Task(**task_data)
            db_session.add(task)
            todo_tasks.append(task)

        # IN_PROGRESS状態のタスクを作成
        progress_tasks = []
        for i in range(2):
            task_data = {
                "title": f"進行中タスク{i}",
                "status": "in_progress",
                "priority": "medium",
                "user_id": test_user["id"],
                "position": i,
            }
            task = Task(**task_data)
            db_session.add(task)
            progress_tasks.append(task)

        await db_session.commit()
        for task in todo_tasks + progress_tasks:
            await db_session.refresh(task)

        # TODOタスク1をIN_PROGRESSの位置1に移動
        reorder_data = {"task_id": str(todo_tasks[1].id), "new_position": 1, "new_status": "in_progress"}

        response = await async_client.patch("/api/v1/tasks/reorder", headers=auth_headers, json=reorder_data)

        assert response.status_code == 200
        data = response.json()

        updated_tasks = {task["id"]: task for task in data["tasks"]}

        # 移動したタスクの確認
        moved_task = updated_tasks[str(todo_tasks[1].id)]
        assert moved_task["status"] == "in_progress"
        assert moved_task["position"] == 1

        # TODO グループの位置調整確認
        assert updated_tasks[str(todo_tasks[0].id)]["position"] == 0  # 変化なし
        assert updated_tasks[str(todo_tasks[2].id)]["position"] == 1  # 1つ前に詰める

        # IN_PROGRESS グループの位置調整確認
        assert updated_tasks[str(progress_tasks[0].id)]["position"] == 0  # 変化なし
        assert updated_tasks[str(progress_tasks[1].id)]["position"] == 2  # 1つ後ろに移動

    @pytest.mark.asyncio
    async def test_reorder_task_not_found(self, async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
        """存在しないタスクの並び替えエラー"""
        from uuid import uuid4

        fake_id = uuid4()
        reorder_data = {"task_id": str(fake_id), "new_position": 1, "new_status": "todo"}

        response = await async_client.patch("/api/v1/tasks/reorder", headers=auth_headers, json=reorder_data)

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_reorder_task_without_auth(self, async_client: AsyncClient, test_task: dict[str, Any]) -> None:
        """認証なしでの並び替えエラー"""
        reorder_data = {"task_id": str(test_task["id"]), "new_position": 1, "new_status": "todo"}

        response = await async_client.patch("/api/v1/tasks/reorder", json=reorder_data)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_reorder_task_invalid_position(
        self, async_client: AsyncClient, auth_headers: dict[str, str], test_task: dict[str, Any]
    ) -> None:
        """無効な位置での並び替えエラー"""
        reorder_data = {
            "task_id": str(test_task["id"]),
            "new_position": -1,  # 無効な位置
            "new_status": "todo",
        }

        response = await async_client.patch("/api/v1/tasks/reorder", headers=auth_headers, json=reorder_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_reorder_task_same_position_no_change(
        self, async_client: AsyncClient, auth_headers: dict[str, str], test_task: dict[str, Any]
    ) -> None:
        """同じ位置への移動（変更なし）"""
        # 現在の位置と同じ位置に移動
        reorder_data = {
            "task_id": str(test_task["id"]),
            "new_position": test_task["task"].position,
            "new_status": test_task["task"].status,
        }

        response = await async_client.patch("/api/v1/tasks/reorder", headers=auth_headers, json=reorder_data)

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @pytest.mark.asyncio
    async def test_reorder_task_access_control(
        self, async_client: AsyncClient, db_session: AsyncSession, test_task: dict[str, Any]
    ) -> None:
        """他のユーザーのタスクを並び替えできないことを確認"""
        # 別のユーザーを作成
        from app.core.security import security_manager
        from app.models.user import User

        other_user_data = {
            "email": "reorderuser@example.com",
            "display_name": "並び替えテストユーザー",
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
                "username": "reorderuser@example.com",
                "password": "password123",
            },
        )
        other_user_token = login_response.json()["access_token"]
        other_user_headers = {"Authorization": f"Bearer {other_user_token}"}

        # 他のユーザーのタスクを並び替え試行
        reorder_data = {"task_id": str(test_task["id"]), "new_position": 1, "new_status": "in_progress"}

        response = await async_client.patch("/api/v1/tasks/reorder", headers=other_user_headers, json=reorder_data)

        assert response.status_code == 400  # タスクが見つからない
