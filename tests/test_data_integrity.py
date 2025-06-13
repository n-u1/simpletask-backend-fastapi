"""データ整合性テスト

リレーション制約、必須フィールド検証、データベース制約のテスト
"""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


class TestDatabaseConstraints:
    """データベース制約テスト"""

    @pytest.mark.asyncio
    async def test_user_email_unique_constraint(self, db_session: AsyncSession) -> None:
        """ユーザーメール重複制約テスト"""
        from app.core.security import security_manager
        from app.models.user import User

        # 最初のユーザー作成
        user1_data = {
            "email": "constraint@example.com",
            "display_name": "ユーザー1",
            "password_hash": security_manager.get_password_hash("password123"),
            "is_active": True,
        }

        user1 = User(**user1_data)
        db_session.add(user1)
        await db_session.commit()

        # 同じメールアドレスで2番目のユーザー作成を試行
        user2_data = {
            "email": "constraint@example.com",
            "display_name": "ユーザー2",
            "password_hash": security_manager.get_password_hash("password456"),
            "is_active": True,
        }

        user2 = User(**user2_data)
        db_session.add(user2)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_tag_name_unique_per_user_constraint(
        self, db_session: AsyncSession, test_user: dict[str, Any]
    ) -> None:
        """ユーザー内タグ名重複制約テスト"""
        from app.models.tag import Tag

        # 最初のタグ作成
        tag1_data = {
            "name": "重複テストタグ",
            "color": "#3B82F6",
            "description": "1番目のタグ",
            "user_id": test_user["id"],
            "is_active": True,
        }

        tag1 = Tag(**tag1_data)
        db_session.add(tag1)
        await db_session.commit()

        # 同じユーザーで同じ名前のタグ作成を試行
        tag2_data = {
            "name": "重複テストタグ",
            "color": "#EF4444",
            "description": "2番目のタグ",
            "user_id": test_user["id"],
            "is_active": True,
        }

        tag2 = Tag(**tag2_data)
        db_session.add(tag2)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_task_user_foreign_key_constraint(self, db_session: AsyncSession) -> None:
        """タスクのユーザー外部キー制約テスト"""
        from uuid import uuid4

        from sqlalchemy.exc import IntegrityError

        from app.models.task import Task

        # 存在しないユーザーIDでタスク作成を試行
        fake_user_id = uuid4()
        task_data = {
            "title": "制約テストタスク",
            "description": "存在しないユーザーのタスク",
            "status": "todo",
            "priority": "medium",
            "user_id": fake_user_id,
            "position": 0,
        }

        task = Task(**task_data)
        db_session.add(task)

        # 外部キー制約違反が発生することを確認
        with pytest.raises((IntegrityError, Exception)) as exc_info:
            await db_session.commit()

        # SQLiteの場合はより具体的なエラーチェック
        assert "FOREIGN KEY constraint failed" in str(exc_info.value) or isinstance(exc_info.value, IntegrityError)

    @pytest.mark.asyncio
    async def test_task_tag_foreign_key_constraints(
        self, db_session: AsyncSession, test_user: dict[str, Any], test_task: dict[str, Any]
    ) -> None:
        """タスクタグ中間テーブルの外部キー制約テスト"""
        from uuid import uuid4

        from app.models.task_tag import TaskTag

        # 存在しないタグIDでタスクタグ関連付けを試行
        fake_tag_id = uuid4()
        task_tag_data = {
            "task_id": test_task["id"],
            "tag_id": fake_tag_id,
        }

        task_tag = TaskTag(**task_tag_data)
        db_session.add(task_tag)

        # 外部キー制約違反が発生することを確認
        with pytest.raises(IntegrityError):
            await db_session.commit()


class TestRequiredFieldValidation:
    """必須フィールドバリデーションテスト"""

    @pytest.mark.asyncio
    async def test_user_required_fields(self, async_client: AsyncClient) -> None:
        """ユーザー必須フィールドテスト"""
        # メールなし
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "password": "password123",
                "display_name": "テストユーザー",
            },
        )
        assert response.status_code == 422

        # パスワードなし
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "display_name": "テストユーザー",
            },
        )
        assert response.status_code == 422

        # 表示名なし
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_task_required_fields(self, async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
        """タスク必須フィールドテスト"""
        # タイトルなし
        response = await async_client.post(
            "/api/v1/tasks/",
            headers=auth_headers,
            json={
                "description": "説明のみ",
                "status": "todo",
                "priority": "medium",
            },
        )
        assert response.status_code == 422

        # ステータスなし（デフォルト値があるため成功するはず）
        response = await async_client.post(
            "/api/v1/tasks/",
            headers=auth_headers,
            json={
                "title": "タイトルのみ",
                "priority": "medium",
            },
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_tag_required_fields(self, async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
        """タグ必須フィールドテスト"""
        # 名前なし
        response = await async_client.post(
            "/api/v1/tags/",
            headers=auth_headers,
            json={
                "color": "#3B82F6",
                "description": "説明のみ",
            },
        )
        assert response.status_code == 422

        # カラーなし（デフォルト値があるため成功するはず）
        response = await async_client.post(
            "/api/v1/tags/",
            headers=auth_headers,
            json={
                "name": "カラーなしタグ",
                "description": "カラーコードなし",
            },
        )
        assert response.status_code == 201


class TestDataValidation:
    """データバリデーションテスト"""

    @pytest.mark.asyncio
    async def test_email_format_validation(self, async_client: AsyncClient) -> None:
        """メールアドレス形式バリデーション"""
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "test@",
            "test.example.com",
            "",
        ]

        for invalid_email in invalid_emails:
            response = await async_client.post(
                "/api/v1/auth/register",
                json={
                    "email": invalid_email,
                    "password": "password123",
                    "display_name": "テストユーザー",
                },
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_password_length_validation(self, async_client: AsyncClient) -> None:
        """パスワード長バリデーション"""
        short_passwords = ["123", "ab", "1234567"]  # 8文字未満

        for short_password in short_passwords:
            response = await async_client.post(
                "/api/v1/auth/register",
                json={
                    "email": "test@example.com",
                    "password": short_password,
                    "display_name": "テストユーザー",
                },
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_task_status_validation(self, async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
        """タスクステータスバリデーション"""
        invalid_statuses = ["invalid_status", "completed", "pending", ""]

        for invalid_status in invalid_statuses:
            response = await async_client.post(
                "/api/v1/tasks/",
                headers=auth_headers,
                json={
                    "title": "テストタスク",
                    "status": invalid_status,
                    "priority": "medium",
                },
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_task_priority_validation(self, async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
        """タスク優先度バリデーション"""
        invalid_priorities = ["invalid_priority", "critical", "normal", ""]

        for invalid_priority in invalid_priorities:
            response = await async_client.post(
                "/api/v1/tasks/",
                headers=auth_headers,
                json={
                    "title": "テストタスク",
                    "status": "todo",
                    "priority": invalid_priority,
                },
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_tag_color_validation(self, async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
        """タグカラーコードバリデーション"""
        invalid_colors = [
            "red",
            "#RGB",
            "#RRGGBBAA",
            "#GGG123",  # 無効な16進数
        ]

        for i, invalid_color in enumerate(invalid_colors):
            print(f"\nテスト中の無効カラー: '{invalid_color}'")

            response = await async_client.post(
                "/api/v1/tags/",
                headers=auth_headers,
                json={
                    "name": f"カラーテスト_{i}_{invalid_color}",
                    "color": invalid_color,
                    "description": "カラーバリデーションテスト",
                },
            )

            print(f"レスポンス status: {response.status_code}")
            if response.status_code != 422:
                print(f"レスポンス content: {response.text}")

            assert response.status_code == 422, f"カラー '{invalid_color}' でバリデーションエラーが発生しませんでした"

        # 有効なカラーコードが正しく処理されることをテスト
        valid_colors = [
            "#FF0000",
            "#00FF00",
            "#0000FF",
            "3B82F6",  # #なし（#が自動補完される）
            "",  # 空文字（デフォルト値が適用される）
        ]

        for i, valid_color in enumerate(valid_colors):
            response = await async_client.post(
                "/api/v1/tags/",
                headers=auth_headers,
                json={
                    "name": f"有効カラーテスト_{i}_{valid_color}",
                    "color": valid_color,
                    "description": "有効カラーテスト",
                },
            )

            assert response.status_code == 201, f"有効なカラー '{valid_color}' で作成に失敗しました"

            # レスポンスに#付きカラーが含まれることを確認
            data = response.json()
            assert data["color"].startswith("#"), f"カラー '{valid_color}' が正しく処理されていません: {data['color']}"

    @pytest.mark.asyncio
    async def test_display_name_length_validation(self, async_client: AsyncClient) -> None:
        """表示名長バリデーション"""
        # 短すぎる表示名
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "password123",
                "display_name": "a",  # 2文字未満
            },
        )
        assert response.status_code == 422

        # 長すぎる表示名
        long_name = "a" * 21  # 20文字超過
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "password123",
                "display_name": long_name,
            },
        )
        assert response.status_code == 422


class TestCascadeDelete:
    """カスケード削除テスト"""

    @pytest.mark.asyncio
    async def test_user_deletion_cascades_to_tasks(
        self, db_session: AsyncSession, test_user: dict[str, Any], test_task: dict[str, Any]
    ) -> None:
        """ユーザー削除時のタスクカスケード削除"""
        from app.models.task import Task
        from app.models.user import User

        # タスクが存在することを確認
        task = await db_session.get(Task, test_task["id"])
        assert task is not None

        # ユーザーを削除
        user = await db_session.get(User, test_user["id"])
        await db_session.delete(user)
        await db_session.commit()

        # セッションをリフレッシュ
        db_session.expire_all()

        # タスクも削除されていることを確認
        task_after_delete = await db_session.get(Task, test_task["id"])
        assert task_after_delete is None

    @pytest.mark.asyncio
    async def test_user_deletion_cascades_to_tags(
        self, db_session: AsyncSession, test_user: dict[str, Any], test_tag: dict[str, Any]
    ) -> None:
        """ユーザー削除時のタグカスケード削除"""
        from app.models.tag import Tag
        from app.models.user import User

        # タグが存在することを確認
        tag = await db_session.get(Tag, test_tag["id"])
        assert tag is not None

        # ユーザーを削除
        user = await db_session.get(User, test_user["id"])
        await db_session.delete(user)
        await db_session.commit()

        # セッションをリフレッシュ
        db_session.expire_all()

        # タグも削除されていることを確認
        tag_after_delete = await db_session.get(Tag, test_tag["id"])
        assert tag_after_delete is None

    @pytest.mark.asyncio
    async def test_task_deletion_cascades_to_task_tags(
        self, db_session: AsyncSession, test_user: dict[str, Any]
    ) -> None:
        """タスク削除時のタスクタグ中間テーブルカスケード削除"""
        from sqlalchemy import select

        from app.models.tag import Tag
        from app.models.task import Task
        from app.models.task_tag import TaskTag

        # タスクとタグを作成
        task_data = {
            "title": "カスケードテストタスク",
            "description": "カスケード削除テスト",
            "status": "todo",
            "priority": "medium",
            "user_id": test_user["id"],
            "position": 0,
        }
        task = Task(**task_data)
        db_session.add(task)

        tag_data = {
            "name": "カスケードテストタグ",
            "color": "#3B82F6",
            "description": "カスケード削除テスト",
            "user_id": test_user["id"],
            "is_active": True,
        }
        tag = Tag(**tag_data)
        db_session.add(tag)
        await db_session.flush()

        # タスクタグ関連付けを作成
        task_tag = TaskTag(task_id=task.id, tag_id=tag.id)
        db_session.add(task_tag)
        await db_session.commit()

        # タスクタグが存在することを確認
        stmt = select(TaskTag).where(TaskTag.task_id == task.id)
        result = await db_session.execute(stmt)
        task_tag_before = result.scalar_one_or_none()
        assert task_tag_before is not None

        # タスクを削除
        await db_session.delete(task)
        await db_session.commit()

        # タスクタグも削除されていることを確認
        stmt = select(TaskTag).where(TaskTag.task_id == task.id)
        result = await db_session.execute(stmt)
        task_tag_after = result.scalar_one_or_none()
        assert task_tag_after is None


class TestBusinessRuleConstraints:
    """ビジネスルール制約テスト"""

    @pytest.mark.asyncio
    async def test_task_position_non_negative(self, async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
        """タスク位置は非負数でなければならない"""
        response = await async_client.post(
            "/api/v1/tasks/",
            headers=auth_headers,
            json={
                "title": "位置テストタスク",
                "status": "todo",
                "priority": "medium",
                "position": -1,
            },
        )
        # バリデーションでエラーになることを期待
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_completed_task_has_completed_at(
        self, async_client: AsyncClient, auth_headers: dict[str, str], test_task: dict[str, Any]
    ) -> None:
        """完了タスクは完了日時を持つ"""
        # タスクを完了状態に更新
        response = await async_client.patch(
            f"/api/v1/tasks/{test_task['id']}/status",
            headers=auth_headers,
            json={"status": "done"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "done"
        assert data["completed_at"] is not None

        # 完了状態から他の状態に戻すと完了日時がクリアされる
        response = await async_client.patch(
            f"/api/v1/tasks/{test_task['id']}/status",
            headers=auth_headers,
            json={"status": "in_progress"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"
        assert data["completed_at"] is None

    @pytest.mark.asyncio
    async def test_tag_must_belong_to_user(
        self, async_client: AsyncClient, db_session: AsyncSession, test_user: dict[str, Any]
    ) -> None:
        """タスクに追加するタグはユーザーのものでなければならない"""
        # 別のユーザーとタグを作成
        from app.core.security import security_manager
        from app.models.tag import Tag
        from app.models.user import User

        other_user_data = {
            "email": "othertaguser@example.com",
            "display_name": "別のタグユーザー",
            "password_hash": security_manager.get_password_hash("password123"),
            "is_active": True,
        }
        other_user = User(**other_user_data)
        db_session.add(other_user)
        await db_session.flush()

        other_tag_data = {
            "name": "他人のタグ",
            "color": "#EF4444",
            "description": "他人のタグです",
            "user_id": other_user.id,
            "is_active": True,
        }
        other_tag = Tag(**other_tag_data)
        db_session.add(other_tag)
        await db_session.commit()

        # 元のユーザーでログイン
        login_response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user["email"],
                "password": test_user["password"],
            },
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 他人のタグを使ってタスク作成を試行
        response = await async_client.post(
            "/api/v1/tasks/",
            headers=headers,
            json={
                "title": "他人のタグ付きタスク",
                "status": "todo",
                "priority": "medium",
                "tag_ids": [str(other_tag.id)],
            },
        )

        # タスク作成は成功する
        assert response.status_code == 201
        data = response.json()

        # 作成されたタスクの詳細を取得
        task_detail_response = await async_client.get(f"/api/v1/tasks/{data['id']}", headers=headers)
        assert task_detail_response.status_code == 200
        task_detail = task_detail_response.json()

        # 他人のタグは関連付けられていないことを確認
        other_tag_ids = [tag["id"] for tag in task_detail.get("tags", [])]
        assert str(other_tag.id) not in other_tag_ids, "他人のタグが関連付けられてしまった"

        # タスクは作成されているが、無効なタグは無視されている
        assert task_detail["title"] == "他人のタグ付きタスク"
        assert len(task_detail.get("tags", [])) == 0  # 有効なタグがないため空


class TestDataIntegrityEdgeCases:
    """データ整合性エッジケーステスト"""

    @pytest.mark.asyncio
    async def test_very_long_strings(self, async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
        """非常に長い文字列の処理"""
        very_long_title = "a" * 201  # タイトル上限超過
        very_long_description = "a" * 2001  # 説明上限超過

        # 長すぎるタイトル
        response = await async_client.post(
            "/api/v1/tasks/",
            headers=auth_headers,
            json={
                "title": very_long_title,
                "status": "todo",
                "priority": "medium",
            },
        )
        assert response.status_code == 422

        # 長すぎる説明
        response = await async_client.post(
            "/api/v1/tasks/",
            headers=auth_headers,
            json={
                "title": "テストタスク",
                "description": very_long_description,
                "status": "todo",
                "priority": "medium",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_special_characters_handling(self, async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
        """特殊文字の処理"""
        special_chars_data = {
            "title": "特殊文字テスト 🚀 ♥ ★ ñ ü é",
            "description": "改行\nタブ\t引用符\"シングル'バックスラッシュ\\",
            "status": "todo",
            "priority": "medium",
        }

        response = await async_client.post("/api/v1/tasks/", headers=auth_headers, json=special_chars_data)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == special_chars_data["title"]
        assert data["description"] == special_chars_data["description"]

    @pytest.mark.asyncio
    async def test_null_and_empty_value_handling(self, async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
        """NULL値と空値の処理"""
        # 説明をNullで作成
        response = await async_client.post(
            "/api/v1/tasks/",
            headers=auth_headers,
            json={
                "title": "説明なしタスク",
                "description": None,
                "status": "todo",
                "priority": "medium",
            },
        )
        assert response.status_code == 201

        # 説明を空文字で作成
        response = await async_client.post(
            "/api/v1/tasks/",
            headers=auth_headers,
            json={
                "title": "空説明タスク",
                "description": "",
                "status": "todo",
                "priority": "medium",
            },
        )
        assert response.status_code == 201
