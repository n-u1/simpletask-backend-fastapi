"""認証フローテスト

ユーザー登録・ログイン・JWT検証・不正アクセステストを実施
"""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestUserRegistration:
    """ユーザー登録テスト"""

    @pytest.mark.asyncio
    async def test_register_success(self, async_client: AsyncClient, sample_user_data: dict[str, str]) -> None:
        """正常なユーザー登録"""
        response = await async_client.post("/api/v1/auth/register", json=sample_user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == sample_user_data["email"]
        assert data["display_name"] == sample_user_data["display_name"]
        assert "id" in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self, async_client: AsyncClient, test_user: dict[str, Any], sample_user_data: dict[str, str]
    ) -> None:
        """重複メールアドレスでの登録エラー"""
        sample_user_data["email"] = test_user["email"]

        response = await async_client.post("/api/v1/auth/register", json=sample_user_data)

        assert response.status_code == 400
        assert "既に使用されています" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, async_client: AsyncClient, sample_user_data: dict[str, str]) -> None:
        """無効なメールアドレスでの登録エラー"""
        sample_user_data["email"] = "invalid-email"

        response = await async_client.post("/api/v1/auth/register", json=sample_user_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_weak_password(self, async_client: AsyncClient, sample_user_data: dict[str, str]) -> None:
        """弱いパスワードでの登録エラー"""
        sample_user_data["password"] = "123"

        response = await async_client.post("/api/v1/auth/register", json=sample_user_data)

        assert response.status_code == 422


class TestUserLogin:
    """ユーザーログインテスト"""

    @pytest.mark.asyncio
    async def test_login_success(self, async_client: AsyncClient, test_user: dict[str, Any]) -> None:
        """正常なログイン"""
        response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user["email"],
                "password": test_user["password"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data

    @pytest.mark.asyncio
    async def test_login_invalid_email(self, async_client: AsyncClient) -> None:
        """存在しないメールアドレスでのログインエラー"""
        response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "password123",
            },
        )

        assert response.status_code == 401
        assert "メールアドレスまたはパスワードが正しくありません" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, async_client: AsyncClient, test_user: dict[str, Any]) -> None:
        """間違ったパスワードでのログインエラー"""
        response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user["email"],
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401
        assert "メールアドレスまたはパスワードが正しくありません" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_login_inactive_user(
        self, async_client: AsyncClient, db_session: AsyncSession, test_user: dict[str, Any]
    ) -> None:
        """非アクティブユーザーのログインエラー"""
        # ユーザーを非アクティブにする
        user = test_user["user"]
        user.is_active = False
        await db_session.commit()

        response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user["email"],
                "password": test_user["password"],
            },
        )

        assert response.status_code == 401


class TestJWTTokens:
    """JWTトークンテスト"""

    @pytest.mark.asyncio
    async def test_access_protected_endpoint_with_valid_token(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """有効なトークンでの保護されたエンドポイントアクセス"""
        response = await async_client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "display_name" in data

    @pytest.mark.asyncio
    async def test_access_protected_endpoint_without_token(self, async_client: AsyncClient) -> None:
        """トークンなしでの保護されたエンドポイントアクセスエラー"""
        response = await async_client.get("/api/v1/auth/me")

        assert response.status_code == 401
        assert "認証が必要です" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_access_protected_endpoint_with_invalid_token(self, async_client: AsyncClient) -> None:
        """無効なトークンでの保護されたエンドポイントアクセスエラー"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = await async_client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == 401
        assert "無効なトークンです" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, async_client: AsyncClient, test_user: dict[str, Any]) -> None:
        """リフレッシュトークンでの新しいアクセストークン取得"""
        # ログインしてリフレッシュトークンを取得
        login_response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user["email"],
                "password": test_user["password"],
            },
        )
        refresh_token = login_response.json()["refresh_token"]

        # リフレッシュトークンで新しいアクセストークンを取得
        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_refresh_token_with_invalid_token(self, async_client: AsyncClient) -> None:
        """無効なリフレッシュトークンでのエラー"""
        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_refresh_token"},
        )

        assert response.status_code == 401


class TestPasswordChange:
    """パスワード変更テスト"""

    @pytest.mark.asyncio
    async def test_change_password_success(
        self, async_client: AsyncClient, auth_headers: dict[str, str], test_user: dict[str, Any]
    ) -> None:
        """正常なパスワード変更"""
        response = await async_client.put(
            "/api/v1/auth/password",
            headers=auth_headers,
            json={
                "current_password": test_user["password"],
                "new_password": "newpassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "変更されました" in data["message"]

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
        """間違った現在のパスワードでのエラー"""
        response = await async_client.put(
            "/api/v1/auth/password",
            headers=auth_headers,
            json={
                "current_password": "wrongpassword",
                "new_password": "newpassword123",
            },
        )

        assert response.status_code == 400
        assert "現在のパスワードが正しくありません" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_change_password_without_auth(self, async_client: AsyncClient) -> None:
        """認証なしでのパスワード変更エラー"""
        response = await async_client.put(
            "/api/v1/auth/password",
            json={
                "current_password": "password123",
                "new_password": "newpassword123",
            },
        )

        assert response.status_code == 401


class TestLogout:
    """ログアウトテスト"""

    @pytest.mark.asyncio
    async def test_logout_success(self, async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
        """正常なログアウト"""
        response = await async_client.post("/api/v1/auth/logout", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "ログアウト" in data["message"]

    @pytest.mark.asyncio
    async def test_logout_without_auth(self, async_client: AsyncClient) -> None:
        """認証なしでのログアウトエラー"""
        response = await async_client.post("/api/v1/auth/logout")

        assert response.status_code == 401
