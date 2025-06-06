"""権限チェック関連ユーティリティ

リソースの所有権確認とアクセス権限チェックの処理を提供
"""

from typing import Any, Protocol
from uuid import UUID

from app.core.constants import ErrorMessages


class HasUserOwnership(Protocol):
    """ユーザー所有権を持つリソースのプロトコル"""

    user_id: UUID


class HasActiveStatus(Protocol):
    """アクティブ状態を持つリソースのプロトコル"""

    is_active: bool


def check_resource_ownership(resource: HasUserOwnership | None, user_id: UUID, resource_name: str = "リソース") -> None:
    """リソースの所有権チェック

    Args:
        resource: チェック対象のリソース
        user_id: 現在のユーザーID
        resource_name: リソース名（エラーメッセージ用）

    Raises:
        ValueError: リソースが見つからない場合
        PermissionError: 所有権がない場合
    """
    if resource is None:
        raise ValueError(f"{resource_name}が見つかりません")

    if resource.user_id != user_id:
        raise PermissionError(f"{resource_name}にアクセスする権限がありません")


def validate_resource_exists(resource: Any | None, resource_name: str = "リソース") -> None:
    """リソースの存在チェック

    Args:
        resource: チェック対象のリソース
        resource_name: リソース名（エラーメッセージ用）

    Raises:
        ValueError: リソースが見つからない場合
    """
    if resource is None:
        raise ValueError(f"{resource_name}が見つかりません")


def check_resource_active_status(resource: HasActiveStatus, resource_name: str = "リソース") -> None:
    """リソースのアクティブ状態チェック

    Args:
        resource: チェック対象のリソース
        resource_name: リソース名（エラーメッセージ用）

    Raises:
        ValueError: リソースが非アクティブな場合
    """
    if not resource.is_active:
        raise ValueError(f"{resource_name}は無効化されています")


def ensure_resource_access(
    resource: Any | None, user_id: UUID, resource_name: str = "リソース", check_active: bool = False
) -> None:
    """リソースへの総合的なアクセスチェック

    存在確認、所有権確認、アクティブ状態確認を一括で実行

    Args:
        resource: チェック対象のリソース
        user_id: 現在のユーザーID
        resource_name: リソース名（エラーメッセージ用）
        check_active: アクティブ状態もチェックするか

    Raises:
        ValueError: リソースが見つからない、または非アクティブな場合
        PermissionError: 所有権がない場合
    """
    # 存在確認
    validate_resource_exists(resource, resource_name)

    # 所有権確認（user_id属性を持つ場合のみ）
    if hasattr(resource, "user_id"):
        check_resource_ownership(resource, user_id, resource_name)

    # アクティブ状態確認（必要かつis_active属性を持つ場合のみ）
    if check_active and hasattr(resource, "is_active") and not getattr(resource, "is_active", True):
        raise ValueError(ErrorMessages.INACTIVE_RESOURCE)


class PermissionChecker:
    """権限チェッククラス

    より複雑な権限チェックロジックのためのクラス
    """

    def __init__(self, user_id: UUID):
        self.user_id = user_id

    def check_task_access(self, task: Any) -> None:
        """タスクアクセス権限チェック"""
        ensure_resource_access(task, self.user_id, "タスク")

    def check_tag_access(self, tag: Any, include_inactive: bool = False) -> None:
        """タグアクセス権限チェック"""
        # 存在確認と所有権確認
        ensure_resource_access(tag, self.user_id, "タグ")

        # アクティブ状態確認（include_inactiveがFalseの場合のみ）
        if not include_inactive and hasattr(tag, "is_active") and not getattr(tag, "is_active", True):
            raise ValueError(ErrorMessages.INACTIVE_RESOURCE)

    def check_user_profile_access(self, target_user: Any) -> None:
        """ユーザープロフィールアクセス権限チェック"""
        validate_resource_exists(target_user, "ユーザー")

        # 自分自身のプロフィールのみアクセス可能
        if hasattr(target_user, "id") and target_user.id != self.user_id:
            raise PermissionError(ErrorMessages.PROFILE_ACCESS_DENIED)

    def validate_tag_ownership_list(self, tag_ids: list[UUID], available_tags: list[Any]) -> None:
        """タグIDリストの所有権一括チェック

        Args:
            tag_ids: チェック対象のタグIDリスト
            available_tags: 利用可能なタグのリスト

        Raises:
            ValueError: 無効なタグが含まれている場合
        """
        available_tag_ids = {tag.id for tag in available_tags}

        for tag_id in tag_ids:
            if tag_id not in available_tag_ids:
                raise ValueError(f"タグ（ID: {tag_id}）が見つかりません")

            # アクティブ状態もチェック
            tag = next((t for t in available_tags if t.id == tag_id), None)
            if tag and hasattr(tag, "is_active") and not tag.is_active:
                tag_name = getattr(tag, "name", str(tag_id))
                raise ValueError(f"タグ「{tag_name}」は無効化されています")


def create_permission_checker(user_id: UUID) -> PermissionChecker:
    """PermissionCheckerインスタンスを作成

    Args:
        user_id: ユーザーID

    Returns:
        PermissionCheckerインスタンス
    """
    return PermissionChecker(user_id)
