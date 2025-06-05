"""ユーザーサービス層

ユーザーのプロフィール管理のビジネスロジックを提供
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.user import user_crud
from app.models.user import User
from app.schemas.user import UserUpdate


class UserService:
    """ユーザーサービスクラス

    認証以外のユーザー管理機能を提供
    - プロフィール更新
    - アカウント削除
    """

    def __init__(self) -> None:
        self.user_crud = user_crud

    async def get_user_profile(self, db: AsyncSession, user_id: UUID) -> User | None:
        """ユーザープロフィールを取得"""
        try:
            user = await self.user_crud.get(db, id=user_id)
            return user
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"ユーザープロフィール取得エラー: {e}")
            return None

    async def update_user_profile(self, db: AsyncSession, user: User, user_update: UserUpdate) -> User:
        """ユーザープロフィールを更新"""
        try:
            # 更新可能フィールドのみ抽出
            update_data = user_update.model_dump(exclude_unset=True)

            # セキュリティ上、特定フィールドのみ更新可能
            allowed_fields = {"display_name", "avatar_url"}
            filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields}

            if not filtered_data:
                raise ValueError("更新するフィールドが指定されていません")

            updated_user = await self.user_crud.update(db, db_obj=user, obj_in=filtered_data)
            return updated_user

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"ユーザープロフィール更新エラー: {e}")
            raise

    async def delete_user_account(self, db: AsyncSession, user: User, *, permanent: bool = False) -> bool:
        """ユーザーアカウントを削除"""
        try:
            if permanent:
                # 物理削除（関連データも削除される）
                deleted_user = await self.user_crud.delete(db, id=user.id)
                return deleted_user is not None
            else:
                # ソフトデリート（アカウント無効化）
                deactivated_user = await self.user_crud.update(db, db_obj=user, obj_in={"is_active": False})
                return deactivated_user is not None

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"ユーザーアカウント削除エラー: {e}")
            raise


user_service = UserService()
