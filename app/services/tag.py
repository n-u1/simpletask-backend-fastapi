"""タグサービス層

タグのビジネスロジックを提供
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import APIConstants, ErrorMessages
from app.crud.tag import tag_crud
from app.models.tag import Tag
from app.schemas.tag import (
    TagCreate,
    TagFilters,
    TagListResponse,
    TagResponse,
    TagSortOptions,
    TagUpdate,
)


class TagService:
    def __init__(self) -> None:
        self.tag_crud = tag_crud

    async def get_tag(
        self, db: AsyncSession, tag_id: UUID, user_id: UUID, *, include_inactive: bool = False
    ) -> Tag | None:
        """タグを取得"""
        tag = await self.tag_crud.get_by_user(db, user_id, tag_id, include_inactive=include_inactive)
        if not tag:
            return None

        # アクセス権限チェック
        if tag.user_id != user_id:
            raise PermissionError(ErrorMessages.TAG_ACCESS_DENIED)

        return tag

    async def get_tags(
        self,
        db: AsyncSession,
        user_id: UUID,
        *,
        skip: int = 0,
        limit: int = APIConstants.DEFAULT_PAGE_SIZE,
        filters: TagFilters | None = None,
        sort_options: TagSortOptions | None = None,
        include_inactive: bool = False,
    ) -> TagListResponse:
        """タグ一覧を取得"""
        # 制限値チェック
        limit = min(limit, APIConstants.MAX_PAGE_SIZE)
        limit = max(limit, APIConstants.MIN_PAGE_SIZE)

        # タグ取得
        tags = await self.tag_crud.get_multi_by_user(
            db,
            user_id,
            skip=skip,
            limit=limit,
            filters=filters,
            sort_options=sort_options,
            include_inactive=include_inactive,
        )

        # 総件数取得
        total = await self.tag_crud.count_by_user(db, user_id, filters, include_inactive=include_inactive)

        # ページネーション計算
        page = (skip // limit) + 1
        total_pages = (total + limit - 1) // limit

        return TagListResponse(
            tags=[TagResponse.model_validate(tag) for tag in tags],
            total=total,
            page=page,
            per_page=limit,
            total_pages=total_pages,
        )

    async def create_tag(self, db: AsyncSession, tag_in: TagCreate, user_id: UUID) -> Tag:
        """タグを作成"""
        try:
            tag = await self.tag_crud.create_for_user(db, tag_in=tag_in, user_id=user_id)
            return tag

        except ValueError as e:
            # 重複エラーを適切なメッセージに変換
            if "既に使用されています" in str(e):
                raise ValueError(ErrorMessages.TAG_NAME_DUPLICATE) from e
            raise

    async def update_tag(self, db: AsyncSession, tag_id: UUID, tag_in: TagUpdate, user_id: UUID) -> Tag:
        """タグを更新"""
        # タグ取得と権限チェック
        tag = await self.get_tag(db, tag_id, user_id, include_inactive=True)
        if not tag:
            raise ValueError(ErrorMessages.TAG_NOT_FOUND)

        try:
            updated_tag = await self.tag_crud.update_for_user(db, db_tag=tag, tag_in=tag_in)
            return updated_tag

        except ValueError as e:
            # 重複エラーを適切なメッセージに変換
            if "既に使用されています" in str(e):
                raise ValueError(ErrorMessages.TAG_NAME_DUPLICATE) from e
            raise

    async def delete_tag(self, db: AsyncSession, tag_id: UUID, user_id: UUID, *, force_delete: bool = False) -> bool:
        """タグを削除"""
        # タグ取得と権限チェック
        tag = await self.get_tag(db, tag_id, user_id, include_inactive=True)
        if not tag:
            raise ValueError(ErrorMessages.TAG_NOT_FOUND)

        # 関連タスクの確認
        if not force_delete and tag.task_count > 0:
            raise ValueError(f"タグ「{tag.name}」は{tag.task_count}個のタスクで使用されているため削除できません")

        if force_delete:
            # 物理削除
            deleted_tag = await self.tag_crud.delete(db, id=tag_id)
            return deleted_tag is not None
        else:
            # ソフトデリート
            await self.tag_crud.soft_delete(db, db_tag=tag)
            return True


tag_service = TagService()
