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
from app.utils.pagination import calculate_pagination, create_pagination_result


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
        from app.utils.permission import create_permission_checker

        permission_checker = create_permission_checker(user_id)
        permission_checker.check_tag_access(tag, include_inactive=include_inactive)

        return tag

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
    ) -> TagListResponse:
        """タグ一覧を取得"""
        # ページネーション計算
        pagination_params = calculate_pagination(page, per_page)

        # タグ取得
        tags = await self.tag_crud.get_multi_by_user(
            db,
            user_id,
            skip=pagination_params.skip,
            limit=pagination_params.limit,
            filters=filters,
            sort_options=sort_options,
            include_inactive=include_inactive,
        )

        # 総件数取得
        total = await self.tag_crud.count_by_user(db, user_id, filters, include_inactive=include_inactive)

        # ページネーション結果作成
        pagination_result = create_pagination_result(pagination_params.page, pagination_params.limit, total)

        return TagListResponse(
            tags=[TagResponse.model_validate(tag) for tag in tags],
            total=pagination_result.total,
            page=pagination_result.page,
            per_page=pagination_result.per_page,
            total_pages=pagination_result.total_pages,
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
            # 論理削除
            await self.tag_crud.soft_delete(db, db_tag=tag)
            return True


tag_service = TagService()
