"""テスト用Pydanticスキーマ置き換え"""

# テスト環境での動的スキーマ置き換えのためRuffルールを無効化
# ruff: noqa: B010

from typing import Any, cast


def setup_schema_overrides() -> None:
    """テスト用スキーマでモジュールのスキーマを置き換え"""
    try:
        # 元のスキーマクラスを取得してから置き換え
        from app.schemas.auth import AuthUserResponse as OriginalAuthUserResponse
        from app.schemas.task import TaskResponse as OriginalTaskResponse
        from app.schemas.user import UserResponse as OriginalUserResponse

        # 元のスキーマを継承したテストスキーマを動的作成
        TestUserResponse = _create_test_user_response(OriginalUserResponse)
        TestAuthUserResponse = _create_test_auth_user_response(OriginalAuthUserResponse)
        TestTaskResponse = _create_test_task_response(OriginalTaskResponse)

        # モジュールでスキーマを置き換え
        import app.api.v1.auth as auth_module
        import app.api.v1.tasks as tasks_module
        import app.api.v1.users as users_module

        # 動的置き換え（型チェッカーのエラーは無視）
        if hasattr(auth_module, "AuthUserResponse"):
            setattr(auth_module, "AuthUserResponse", TestAuthUserResponse)
            print("✅ AuthUserResponseスキーマ置き換え完了")

        if hasattr(users_module, "UserResponse"):
            setattr(users_module, "UserResponse", TestUserResponse)
            print("✅ UserResponseスキーマ置き換え完了")

        if hasattr(tasks_module, "TaskResponse"):
            setattr(tasks_module, "TaskResponse", TestTaskResponse)
            print("✅ TaskResponseスキーマ置き換え完了")

        print("✅ TagResponseは本来のスキーマを使用")

    except ImportError as e:
        print(f"⚠️ スキーマ置き換えでエラー: {e}")


def _create_test_user_response(base_class: type[Any]) -> type[Any]:
    """UserResponse用のテストスキーマクラスを動的作成"""

    class TestUserResponse(base_class):
        """テスト用UserResponseスキーマ（継承版）"""

        # 必要に応じて追加フィールドやメソッドをオーバーライドする
        pass

    return TestUserResponse


def _create_test_auth_user_response(base_class: type[Any]) -> type[Any]:
    """AuthUserResponse用のテストスキーマクラスを動的作成"""

    class TestAuthUserResponse(base_class):
        """テスト用AuthUserResponseスキーマ（継承版）"""

        # 必要に応じて追加フィールドやメソッドをオーバーライドする
        pass

    return TestAuthUserResponse


def _create_test_task_response(base_class: type[Any]) -> type[Any]:
    """TaskResponse用のテストスキーマクラスを動的作成"""

    class TestTaskResponse(base_class):
        """テスト用TaskResponseスキーマ（継承版）"""

        @classmethod
        def model_validate(
            cls,
            obj: Any,
            *,
            strict: bool | None = None,
            from_attributes: bool | None = None,
            context: Any | None = None,
            by_alias: bool | None = None,
            by_name: bool | None = None,
        ) -> Any:
            """TaskResponse用のカスタムバリデーション"""
            if hasattr(obj, "id"):
                # 基底クラスのバリデーションを実行
                instance = super().model_validate(
                    obj,
                    strict=strict,
                    from_attributes=from_attributes,
                    context=context,
                    by_alias=by_alias,
                    by_name=by_name,
                )

                # タグ情報の処理（テスト環境用の追加処理）
                _process_task_tags(instance, obj)
                return cast("Any", instance)

            result = super().model_validate(
                obj,
                strict=strict,
                from_attributes=from_attributes,
                context=context,
                by_alias=by_alias,
                by_name=by_name,
            )
            return cast("Any", result)

    return TestTaskResponse


def _process_task_tags(instance: Any, obj: Any) -> None:
    """タスクタグ情報を処理（テスト環境用）"""
    try:
        if hasattr(obj, "task_tags") and obj.task_tags:
            tags = []
            tag_names = []
            for task_tag in obj.task_tags:
                if hasattr(task_tag, "tag") and task_tag.tag:
                    # タグ情報を追加
                    tag_dict = {
                        "id": task_tag.tag.id,
                        "name": task_tag.tag.name,
                        "color": task_tag.tag.color,
                        "description": task_tag.tag.description,
                    }
                    tags.append(tag_dict)
                    tag_names.append(task_tag.tag.name)

            # インスタンスにタグ情報を設定（存在する場合のみ）
            if hasattr(instance, "tags"):
                instance.tags = tags
            if hasattr(instance, "tag_names"):
                instance.tag_names = tag_names
    except Exception:
        # タグ処理でエラーが発生しても継続
        pass
