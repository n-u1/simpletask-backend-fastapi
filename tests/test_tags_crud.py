"""タグCRUD基本動作テスト

タグの作成・取得・更新・削除とユーザー固有データのアクセス制御テスト
"""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestTagCreate:
    """タグ作成テスト"""

    @pytest.mark.asyncio
    async def test_create_tag_success(
        self, async_client: AsyncClient, auth_headers: dict[str, str], sample_tag_data: dict[str, str]
    ) -> None:
        """正常なタグ作成"""
        response = await async_client.post("/api/v1/tags/", headers=auth_headers, json=sample_tag_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_tag_data["name"]
        assert data["color"] == sample_tag_data["color"]
        assert data["description"] == sample_tag_data["description"]
        assert "id" in data
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_tag_without_auth(self, async_client: AsyncClient, sample_tag_data: dict[str, str]) -> None:
        """認証なしでのタグ作成エラー"""
        response = await async_client.post("/api/v1/tags/", json=sample_tag_data)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_tag_duplicate_name(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        test_tag: dict[str, Any],
        sample_tag_data: dict[str, str],
    ) -> None:
        """重複タグ名での作成エラー"""
        sample_tag_data["name"] = test_tag["tag"].name

        response = await async_client.post("/api/v1/tags/", headers=auth_headers, json=sample_tag_data)

        assert response.status_code == 400
        assert "既に使用されています" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_create_tag_invalid_color(
        self, async_client: AsyncClient, auth_headers: dict[str, str], sample_tag_data: dict[str, str]
    ) -> None:
        """無効なカラーコードでのタグ作成エラー"""
        sample_tag_data["color"] = "invalid-color"

        response = await async_client.post("/api/v1/tags/", headers=auth_headers, json=sample_tag_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_tag_empty_name(
        self, async_client: AsyncClient, auth_headers: dict[str, str], sample_tag_data: dict[str, str]
    ) -> None:
        """空のタグ名での作成エラー"""
        sample_tag_data["name"] = ""

        response = await async_client.post("/api/v1/tags/", headers=auth_headers, json=sample_tag_data)

        assert response.status_code == 422


class TestTagRead:
    """タグ取得テスト"""

    @pytest.mark.asyncio
    async def test_get_tags_success(
        self, async_client: AsyncClient, auth_headers: dict[str, str], test_tag: dict[str, Any]
    ) -> None:
        """タグ一覧取得成功"""
        response = await async_client.get("/api/v1/tags/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "tags" in data
        assert "total" in data
        assert len(data["tags"]) >= 1

        # テストタグが含まれていることを確認
        tag_names = [tag["name"] for tag in data["tags"]]
        assert test_tag["tag"].name in tag_names

    @pytest.mark.asyncio
    async def test_get_tag_by_id_success(
        self, async_client: AsyncClient, auth_headers: dict[str, str], test_tag: dict[str, Any]
    ) -> None:
        """特定タグ取得成功"""
        response = await async_client.get(f"/api/v1/tags/{test_tag['id']}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_tag["id"])
        assert data["name"] == test_tag["tag"].name

    @pytest.mark.asyncio
    async def test_get_tag_not_found(self, async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
        """存在しないタグ取得エラー"""
        from uuid import uuid4

        fake_id = uuid4()

        response = await async_client.get(f"/api/v1/tags/{fake_id}", headers=auth_headers)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_tags_without_auth(self, async_client: AsyncClient) -> None:
        """認証なしでのタグ取得エラー"""
        response = await async_client.get("/api/v1/tags/")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_tags_with_filters(
        self, async_client: AsyncClient, auth_headers: dict[str, str], test_tag: dict[str, Any]
    ) -> None:
        """フィルタ付きタグ取得"""
        response = await async_client.get(f"/api/v1/tags/?colors={test_tag['tag'].color}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # 指定した色のタグのみ返されることを確認
        for tag in data["tags"]:
            assert tag["color"] == test_tag["tag"].color

    @pytest.mark.asyncio
    async def test_get_tags_pagination(self, async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
        """タグ一覧のページネーション"""
        response = await async_client.get("/api/v1/tags/?page=1&per_page=5", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 5


class TestTagUpdate:
    """タグ更新テスト"""

    @pytest.mark.asyncio
    async def test_update_tag_success(
        self, async_client: AsyncClient, auth_headers: dict[str, str], test_tag: dict[str, Any]
    ) -> None:
        """タグ更新成功"""
        update_data = {
            "name": "更新されたタグ",
            "color": "#10B981",
            "description": "更新されたタグの説明",
        }

        response = await async_client.put(f"/api/v1/tags/{test_tag['id']}", headers=auth_headers, json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["color"] == update_data["color"]
        assert data["description"] == update_data["description"]

    @pytest.mark.asyncio
    async def test_update_tag_duplicate_name(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        db_session: AsyncSession,
        test_user: dict[str, Any],
        test_tag: dict[str, Any],
    ) -> None:
        """重複タグ名での更新エラー"""
        # 別のタグを作成
        from app.models.tag import Tag

        another_tag_data = {
            "name": "別のタグ",
            "color": "#F59E0B",
            "description": "別のタグの説明",
            "user_id": test_user["id"],
            "is_active": True,
        }

        another_tag = Tag(**another_tag_data)
        db_session.add(another_tag)
        await db_session.commit()

        # 既存のタグ名で更新を試行
        update_data = {"name": another_tag.name}

        response = await async_client.put(f"/api/v1/tags/{test_tag['id']}", headers=auth_headers, json=update_data)

        assert response.status_code == 400
        assert "既に使用されています" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_update_tag_not_found(self, async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
        """存在しないタグ更新エラー"""
        from uuid import uuid4

        fake_id = uuid4()

        response = await async_client.put(
            f"/api/v1/tags/{fake_id}",
            headers=auth_headers,
            json={"name": "更新タグ"},
        )

        assert response.status_code in [400, 404]

    @pytest.mark.asyncio
    async def test_update_tag_without_auth(self, async_client: AsyncClient, test_tag: dict[str, Any]) -> None:
        """認証なしでのタグ更新エラー"""
        response = await async_client.put(
            f"/api/v1/tags/{test_tag['id']}",
            json={"name": "更新タグ"},
        )

        assert response.status_code == 401


class TestTagDelete:
    """タグ削除テスト"""

    @pytest.mark.asyncio
    async def test_delete_tag_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        db_session: AsyncSession,
        test_user: dict[str, Any],
    ) -> None:
        """タグ削除成功"""
        # 削除用のタグを作成
        from app.models.tag import Tag

        tag_data = {
            "name": "削除予定タグ",
            "color": "#EC4899",
            "description": "削除テスト用",
            "user_id": test_user["id"],
            "is_active": True,
        }

        tag = Tag(**tag_data)
        db_session.add(tag)
        await db_session.commit()
        await db_session.refresh(tag)

        # タグ削除
        response = await async_client.delete(f"/api/v1/tags/{tag.id}", headers=auth_headers)

        assert response.status_code == 204

        # 削除確認（論理削除の場合、is_activeがFalseになる）
        get_response = await async_client.get(f"/api/v1/tags/{tag.id}", headers=auth_headers)
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_tag_not_found(self, async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
        """存在しないタグ削除エラー"""
        from uuid import uuid4

        fake_id = uuid4()

        response = await async_client.delete(f"/api/v1/tags/{fake_id}", headers=auth_headers)

        assert response.status_code in [400, 403, 404]

    @pytest.mark.asyncio
    async def test_delete_tag_without_auth(self, async_client: AsyncClient, test_tag: dict[str, Any]) -> None:
        """認証なしでのタグ削除エラー"""
        response = await async_client.delete(f"/api/v1/tags/{test_tag['id']}")

        assert response.status_code == 401


class TestTagAccessControl:
    """タグアクセス制御テスト"""

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_user_tag(
        self, async_client: AsyncClient, db_session: AsyncSession, test_tag: dict[str, Any]
    ) -> None:
        """他のユーザーのタグにアクセスできないことを確認"""
        # 別のユーザーを作成
        from app.core.security import security_manager
        from app.models.user import User

        other_user_data = {
            "email": "tagotheruser@example.com",
            "display_name": "タグ別ユーザー",
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
                "username": "tagotheruser@example.com",
                "password": "password123",
            },
        )
        other_user_token = login_response.json()["access_token"]
        other_user_headers = {"Authorization": f"Bearer {other_user_token}"}

        # 他のユーザーのタグへアクセス試行
        response = await async_client.get(f"/api/v1/tags/{test_tag['id']}", headers=other_user_headers)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_can_only_see_own_tags(
        self, async_client: AsyncClient, db_session: AsyncSession, test_tag: dict[str, Any]
    ) -> None:
        """ユーザーは自分のタグのみ表示されることを確認"""
        # 別のユーザーを作成
        from app.core.security import security_manager
        from app.models.tag import Tag
        from app.models.user import User

        other_user_data = {
            "email": "tagotheruser2@example.com",
            "display_name": "タグ別ユーザー2",
            "password_hash": security_manager.get_password_hash("password123"),
            "is_active": True,
        }

        other_user = User(**other_user_data)
        db_session.add(other_user)
        await db_session.flush()

        # 別のユーザーのタグを作成
        other_tag_data = {
            "name": "他のユーザーのタグ",
            "color": "#8B5CF6",
            "description": "アクセスできないはず",
            "user_id": other_user.id,
            "is_active": True,
        }

        other_tag = Tag(**other_tag_data)
        db_session.add(other_tag)
        await db_session.commit()

        # 元のユーザーでログイン
        from app.models.user import User as UserModel

        original_user = await db_session.get(UserModel, test_tag["tag"].user_id)

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

        # タグ一覧取得
        response = await async_client.get("/api/v1/tags/", headers=headers)

        assert response.status_code == 200
        data = response.json()

        # 自分のタグのみ表示されることを確認
        tag_names = [tag["name"] for tag in data["tags"]]
        assert test_tag["tag"].name in tag_names
        assert "他のユーザーのタグ" not in tag_names


class TestTagTaskIntegration:
    """タグとタスクの連携テスト"""

    @pytest.mark.asyncio
    async def test_create_task_with_tag(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        test_tag: dict[str, Any],
    ) -> None:
        """タグ付きタスク作成"""
        task_data = {
            "title": "タグ付きタスク",
            "description": "タグが付いたタスク",
            "status": "todo",
            "priority": "medium",
            "tag_ids": [str(test_tag["id"])],
        }

        response = await async_client.post("/api/v1/tasks/", headers=auth_headers, json=task_data)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == task_data["title"]

        # 作成後のタスク詳細を取得してタグ情報を確認
        task_detail_response = await async_client.get(f"/api/v1/tasks/{data['id']}", headers=auth_headers)
        assert task_detail_response.status_code == 200
        task_detail = task_detail_response.json()

        # 必ずタグ情報が含まれている
        assert "tags" in task_detail
        assert len(task_detail["tags"]) == 1
        assert task_detail["tags"][0]["id"] == str(test_tag["id"])
        assert task_detail["tags"][0]["name"] == test_tag["tag"].name

    @pytest.mark.asyncio
    async def test_filter_tasks_by_tag(
        self, async_client: AsyncClient, auth_headers: dict[str, str], test_tag: dict[str, Any]
    ) -> None:
        """タグでタスクをフィルタリング"""
        # タグ付きタスクを作成
        task_data = {
            "title": "フィルタテスト用タスク",
            "description": "タグフィルタのテスト",
            "status": "todo",
            "priority": "medium",
            "tag_ids": [str(test_tag["id"])],
        }

        await async_client.post("/api/v1/tasks/", headers=auth_headers, json=task_data)

        # タグでフィルタリング
        response = await async_client.get(f"/api/v1/tasks/?tag_ids={test_tag['id']}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # フィルタされたタスクにはすべて指定したタグが含まれている
        for task in data["tasks"]:
            tag_ids = [tag["id"] for tag in task["tags"]]
            assert str(test_tag["id"]) in tag_ids

    @pytest.mark.asyncio
    async def test_mixed_valid_invalid_tags(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        db_session: AsyncSession,
        test_user: dict[str, Any],
        test_tag: dict[str, Any],
    ) -> None:
        """有効なタグと無効なタグが混在する場合のテスト"""
        # 別のユーザーのタグを作成
        from app.core.security import security_manager
        from app.models.tag import Tag
        from app.models.user import User

        other_user = User(
            email="mixedtags@example.com",
            display_name="別ユーザー",
            password_hash=security_manager.get_password_hash("password123"),
            is_active=True,
        )
        db_session.add(other_user)
        await db_session.flush()

        invalid_tag = Tag(
            name="無効なタグ",
            color="#FF0000",
            user_id=other_user.id,
            is_active=True,
        )
        db_session.add(invalid_tag)
        await db_session.commit()

        # 有効なタグと無効なタグを混在させてタスク作成
        task_data = {
            "title": "混在タグテスト",
            "status": "todo",
            "priority": "medium",
            "tag_ids": [str(test_tag["id"]), str(invalid_tag.id)],  # 有効 + 無効
        }

        response = await async_client.post("/api/v1/tasks/", headers=auth_headers, json=task_data)

        assert response.status_code == 201
        data = response.json()

        # タスク詳細を取得
        detail_response = await async_client.get(f"/api/v1/tasks/{data['id']}", headers=auth_headers)
        assert detail_response.status_code == 200
        detail_data = detail_response.json()

        # 有効なタグのみが関連付けられることを確認
        if "tags" in detail_data and len(detail_data["tags"]) > 0:
            tag_ids = [tag["id"] for tag in detail_data["tags"]]
            assert str(test_tag["id"]) in tag_ids
            assert str(invalid_tag.id) not in tag_ids
            assert len(detail_data["tags"]) == 1  # 有効なタグのみ
