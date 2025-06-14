"""タグサービス層

タグのビジネスロジックを提供
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import APIConstants, ErrorMessages
from app.crud.tag import tag_crud
from app.dtos.tag import TagDTO, TagListDTO
from app.repositories.tag import tag_repository
from app.schemas.tag import TagCreate, TagFilters, TagSortOptions, TagUpdate


class TagService:
    """タグサービス

    ビジネスロジックのみに専念
    データ変換はリポジトリ層で実施
    """

    def __init__(self) -> None:
        self.tag_crud = tag_crud
        self.tag_repository = tag_repository

    async def get_tag(
        self, db: AsyncSession, tag_id: UUID, user_id: UUID, *, include_inactive: bool = False
    ) -> TagDTO | None:
        """タグを取得

        Args:
            db: データベースセッション
            tag_id: タグID
            user_id: ユーザーID
            include_inactive: 非アクティブタグも含めるかどうか

        Returns:
            TagDTO または None

        Raises:
            PermissionError: アクセス権限がない場合
        """
        # DTOで取得
        tag_dto = await self.tag_repository.get_by_id(db, tag_id, user_id)
        if not tag_dto:
            return None

        # アクティブ状態チェック
        if not include_inactive and not tag_dto.is_active:
            return None

        # アクセス権限チェック
        if tag_dto.user_id != user_id:
            raise PermissionError(ErrorMessages.TAG_ACCESS_DENIED)

        return tag_dto

    async def get_tags(
        self,
        db: AsyncSession,
        user_id: UUID,
        *,
        page: int = 1,
        per_page: int = APIConstants.DEFAULT_PAGE_SIZE,
        filters: TagFilters | None = None,
        sort_options: TagSortOptions | None = None,
        include_inactive: bool = False,
    ) -> TagListDTO:
        """タグ一覧を取得

        Args:
            db: データベースセッション
            user_id: ユーザーID
            page: ページ番号
            per_page: 1ページあたりの件数
            filters: フィルタ条件
            sort_options: ソート条件
            include_inactive: 非アクティブタグも含めるかどうか

        Returns:
            TagListDTO
        """
        # ページネーション計算
        skip = (page - 1) * per_page

        # リポジトリから取得
        return await self.tag_repository.get_list(
            db,
            user_id,
            skip=skip,
            limit=per_page,
            filters=filters,
            sort_options=sort_options,
            include_inactive=include_inactive,
        )

    async def create_tag(self, db: AsyncSession, tag_in: TagCreate, user_id: UUID) -> TagDTO:
        """タグを作成

        Args:
            db: データベースセッション
            tag_in: タグ作成データ
            user_id: ユーザーID

        Returns:
            作成されたTagDTO

        Raises:
            ValueError: バリデーションエラーまたは重複エラー
        """
        try:
            # タグ作成
            tag = await self.tag_crud.create_for_user(db, tag_in=tag_in, user_id=user_id)

            # DTOで取得して返却
            created_tag_dto = await self.tag_repository.get_by_id(db, tag.id, user_id)
            if not created_tag_dto:
                raise ValueError("タグの作成に失敗しました")

            return created_tag_dto

        except ValueError as e:
            # 重複エラーを適切なメッセージに変換
            if "既に使用されています" in str(e):
                raise ValueError(ErrorMessages.TAG_NAME_DUPLICATE) from e
            raise

    async def update_tag(self, db: AsyncSession, tag_id: UUID, tag_in: TagUpdate, user_id: UUID) -> TagDTO:
        """タグを更新

        Args:
            db: データベースセッション
            tag_id: タグID
            tag_in: タグ更新データ
            user_id: ユーザーID

        Returns:
            更新されたTagDTO

        Raises:
            ValueError: タグが見つからない場合やバリデーションエラー
            PermissionError: アクセス権限がない場合
        """
        # タグ取得と権限チェック
        existing_tag_dto = await self.get_tag(db, tag_id, user_id, include_inactive=True)
        if not existing_tag_dto:
            raise ValueError(ErrorMessages.TAG_NOT_FOUND)

        # CRUDレイヤーで更新処理（SQLAlchemyモデルが必要）
        tag = await self.tag_crud.get_by_user(db, user_id, tag_id, include_inactive=True)
        if not tag:
            raise ValueError(ErrorMessages.TAG_NOT_FOUND)

        try:
            await self.tag_crud.update_for_user(db, db_tag=tag, tag_in=tag_in)

            # 更新後のDTOを取得して返却
            updated_tag_dto = await self.tag_repository.get_by_id(db, tag_id, user_id)
            if not updated_tag_dto:
                raise ValueError("タグの更新に失敗しました")

            return updated_tag_dto

        except ValueError as e:
            if "既に使用されています" in str(e):
                raise ValueError(ErrorMessages.TAG_NAME_DUPLICATE) from e
            raise

    async def delete_tag(self, db: AsyncSession, tag_id: UUID, user_id: UUID, *, force_delete: bool = False) -> bool:
        """タグを削除

        Args:
            db: データベースセッション
            tag_id: タグID
            user_id: ユーザーID
            force_delete: 物理削除フラグ

        Returns:
            削除成功フラグ

        Raises:
            ValueError: タグが見つからない場合や削除できない場合
            PermissionError: アクセス権限がない場合
        """
        # タグ取得と権限チェック
        tag_dto = await self.get_tag(db, tag_id, user_id, include_inactive=True)
        if not tag_dto:
            raise ValueError(ErrorMessages.TAG_NOT_FOUND)

        # 関連タスクの確認
        if not force_delete and tag_dto.task_count > 0:
            raise ValueError(
                f"タグ「{tag_dto.name}」は{tag_dto.task_count}個のタスクで使用されているため削除できません"
            )

        # CRUDレイヤーで削除処理（SQLAlchemyモデルが必要）
        tag = await self.tag_crud.get_by_user(db, user_id, tag_id, include_inactive=True)
        if not tag:
            raise ValueError(ErrorMessages.TAG_NOT_FOUND)

        if force_delete:
            # 物理削除
            deleted_tag = await self.tag_crud.delete(db, id=tag_id)
            return deleted_tag is not None
        else:
            # 論理削除
            await self.tag_crud.soft_delete(db, db_tag=tag)
            return True


# シングルトンインスタンス
tag_service = TagService()
