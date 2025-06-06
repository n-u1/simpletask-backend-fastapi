"""ユーザーサービス層

ユーザーのプロフィール管理のビジネスロジックを提供
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.user import user_crud
from app.models.user import User
from app.schemas.user import UserUpdate
from app.utils.error_handler import handle_service_error
from app.utils.permission import create_permission_checker


class UserService:
    """ユーザーサービスクラス

    認証以外のユーザー管理機能を提供
    - プロフィール更新
    - アカウント削除
    """

    def __init__(self) -> None:
        self.user_crud = user_crud

    @handle_service_error("ユーザープロフィール取得")
    async def get_user_profile(self, db: AsyncSession, user_id: UUID) -> User | None:
        """ユーザープロフィールを取得"""
        user: User | None = await self.user_crud.get(db, id=user_id)
        return user

    @handle_service_error("ユーザープロフィール更新")
    async def update_user_profile(self, db: AsyncSession, user: User, user_update: UserUpdate) -> User:
        """ユーザープロフィールを更新"""
        # 権限チェック
        permission_checker = create_permission_checker(user.id)
        permission_checker.check_user_profile_access(user)

        # 更新可能フィールドのみ抽出
        update_data = user_update.model_dump(exclude_unset=True)

        # セキュリティ上、特定フィールドのみ更新可能
        allowed_fields = {"display_name", "avatar_url"}
        filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields}

        if not filtered_data:
            raise ValueError("更新するフィールドが指定されていません")

        updated_user: User = await self.user_crud.update(db, db_obj=user, obj_in=filtered_data)
        return updated_user

    @handle_service_error("ユーザーアカウント削除")
    async def delete_user_account(self, db: AsyncSession, user: User, *, permanent: bool = False) -> bool:
        """ユーザーアカウントを削除"""
        # 権限チェック
        permission_checker = create_permission_checker(user.id)
        permission_checker.check_user_profile_access(user)

        if permanent:
            # 物理削除（関連データも削除される）
            deleted_user: User | None = await self.user_crud.delete(db, id=user.id)
            return deleted_user is not None
        else:
            # 論理削除（アカウント無効化）
            deactivated_user: User = await self.user_crud.update(db, db_obj=user, obj_in={"is_active": False})
            return deactivated_user is not None


user_service = UserService()
