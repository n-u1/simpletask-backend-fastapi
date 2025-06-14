"""ユーザーサービス層

ユーザーのビジネスロジックを提供
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ErrorMessages
from app.crud.user import user_crud
from app.dtos.user import UserDTO
from app.repositories.user import user_repository
from app.schemas.user import UserUpdate


class UserService:
    """ユーザーサービス

    ビジネスロジックのみに専念
    データ変換はリポジトリ層で実施
    """

    def __init__(self) -> None:
        self.user_crud = user_crud
        self.user_repository = user_repository

    async def get_user_profile(self, db: AsyncSession, user_id: UUID) -> UserDTO | None:
        """ユーザープロフィールを取得

        Args:
            db: データベースセッション
            user_id: ユーザーID

        Returns:
            UserDTO または None
        """
        return await self.user_repository.get_by_id(db, user_id)

    async def update_user_profile(self, db: AsyncSession, user_id: UUID, user_update: UserUpdate) -> UserDTO:
        """ユーザープロフィールを更新

        Args:
            db: データベースセッション
            user_id: ユーザーID
            user_update: ユーザー更新データ

        Returns:
            更新されたUserDTO

        Raises:
            ValueError: ユーザーが見つからない場合やバリデーションエラー
        """
        # ユーザー取得
        user_dto = await self.user_repository.get_by_id(db, user_id)
        if not user_dto:
            raise ValueError(ErrorMessages.USER_NOT_FOUND)

        # CRUDレイヤーで更新処理（SQLAlchemyモデルが必要）
        user = await self.user_crud.get(db, id=user_id)
        if not user:
            raise ValueError(ErrorMessages.USER_NOT_FOUND)

        try:
            # 更新データの準備
            update_data = user_update.model_dump(exclude_unset=True)

            # SQLAlchemyモデルの更新
            for field, value in update_data.items():
                if hasattr(user, field):
                    setattr(user, field, value)

            await db.commit()
            await db.refresh(user)

            # 更新後のDTOを取得して返却
            updated_user_dto = await self.user_repository.get_by_id(db, user_id)
            if not updated_user_dto:
                raise ValueError("ユーザープロフィールの更新に失敗しました")

            return updated_user_dto

        except ValueError as e:
            await db.rollback()
            raise ValueError(str(e)) from e
        except Exception as e:
            await db.rollback()
            raise ValueError("ユーザープロフィールの更新に失敗しました") from e

    async def delete_user_account(self, db: AsyncSession, user_id: UUID, *, permanent: bool = False) -> bool:
        """ユーザーアカウントを削除

        Args:
            db: データベースセッション
            user_id: ユーザーID
            permanent: 物理削除フラグ

        Returns:
            削除成功フラグ

        Raises:
            ValueError: ユーザーが見つからない場合
        """
        # ユーザー取得
        user_dto = await self.user_repository.get_by_id(db, user_id)
        if not user_dto:
            raise ValueError(ErrorMessages.USER_NOT_FOUND)

        # CRUDレイヤーで削除処理
        user = await self.user_crud.get(db, id=user_id)
        if not user:
            raise ValueError(ErrorMessages.USER_NOT_FOUND)

        try:
            if permanent:
                # 物理削除
                await self.user_crud.delete(db, id=user_id)
            else:
                # 論理削除（アカウント無効化）
                user.is_active = False
                await db.commit()

            return True

        except Exception as e:
            await db.rollback()
            raise ValueError("アカウント削除に失敗しました") from e


# シングルトンインスタンス
user_service = UserService()
