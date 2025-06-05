"""タグCRUDクラス

タグのデータアクセス層を提供
"""

from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import APIConstants
from app.crud.base import CRUDBase
from app.models.tag import Tag
from app.models.task_tag import TaskTag
from app.schemas.tag import TagCreate, TagFilters, TagSortOptions, TagUpdate


class CRUDTag(CRUDBase[Tag, TagCreate, TagUpdate]):
    async def get_by_user(
        self, db: AsyncSession, user_id: UUID, tag_id: UUID, *, include_inactive: bool = False
    ) -> Tag | None:
        """ユーザーIDとタグIDでタグを取得"""
        try:
            conditions = [self.model.id == tag_id, self.model.user_id == user_id]

            # アクティブ状態フィルタ
            if not include_inactive:
                conditions.append(self.model.is_active == True)  # noqa: E712

            stmt = (
                select(self.model)
                .options(selectinload(self.model.task_tags).selectinload(TaskTag.task))
                .where(and_(*conditions))
            )

            result = await db.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"ユーザータグ取得エラー: {e}")
            return None

    async def get_by_name(
        self, db: AsyncSession, user_id: UUID, name: str, *, exclude_id: UUID | None = None
    ) -> Tag | None:
        """ユーザーIDとタグ名でタグを取得（重複チェック用）"""
        try:
            conditions = [
                self.model.user_id == user_id,
                self.model.name == name,
                self.model.is_active == True,  # noqa: E712
            ]

            # 特定IDを除外（更新時の重複チェック用）
            if exclude_id:
                conditions.append(self.model.id != exclude_id)

            stmt = select(self.model).where(and_(*conditions))
            result = await db.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"タグ名検索エラー: {e}")
            return None

    async def get_multi_by_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        *,
        skip: int = 0,
        limit: int = APIConstants.DEFAULT_PAGE_SIZE,
        filters: TagFilters | None = None,
        sort_options: TagSortOptions | None = None,
        include_inactive: bool = False,
    ) -> list[Tag]:
        """ユーザーのタグ一覧を取得"""
        try:
            # ベースクエリ
            stmt = (
                select(self.model)
                .options(selectinload(self.model.task_tags).selectinload(TaskTag.task))
                .where(self.model.user_id == user_id)
            )

            # アクティブ状態フィルタ
            if not include_inactive:
                stmt = stmt.where(self.model.is_active == True)  # noqa: E712

            # フィルタリング適用
            if filters:
                stmt = self._apply_filters(stmt, filters)

            # ソート適用
            stmt = self._apply_sort(stmt, sort_options) if sort_options else stmt.order_by(self.model.created_at.desc())

            # ページネーション
            stmt = stmt.offset(skip).limit(limit)

            result = await db.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"ユーザータグ一覧取得エラー: {e}")
            return []

    async def count_by_user(
        self, db: AsyncSession, user_id: UUID, filters: TagFilters | None = None, *, include_inactive: bool = False
    ) -> int:
        """ユーザーのタグ総数を取得"""
        try:
            stmt = select(func.count(self.model.id)).where(self.model.user_id == user_id)

            # アクティブ状態フィルタ
            if not include_inactive:
                stmt = stmt.where(self.model.is_active == True)  # noqa: E712

            # フィルタリング適用
            if filters:
                stmt = self._apply_filters(stmt, filters)

            result = await db.execute(stmt)
            return result.scalar() or 0

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"ユーザータグ数取得エラー: {e}")
            return 0

    async def create_for_user(self, db: AsyncSession, *, tag_in: TagCreate, user_id: UUID) -> Tag:
        """ユーザー用のタグを作成"""
        try:
            # 名前の重複チェック
            existing_tag = await self.get_by_name(db, user_id, tag_in.name)
            if existing_tag:
                raise ValueError(f"タグ名 '{tag_in.name}' は既に使用されています")

            # タグ作成
            tag_data = tag_in.model_dump()
            tag_data["user_id"] = user_id

            db_tag = self.model(**tag_data)
            db.add(db_tag)
            await db.commit()
            await db.refresh(db_tag)

            return db_tag

        except Exception as e:
            await db.rollback()
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"ユーザータグ作成エラー: {e}")
            raise

    async def update_for_user(self, db: AsyncSession, *, db_tag: Tag, tag_in: TagUpdate) -> Tag:
        """ユーザータグを更新"""
        try:
            # 名前が変更される場合の重複チェック
            if tag_in.name and tag_in.name != db_tag.name:
                existing_tag = await self.get_by_name(db, db_tag.user_id, tag_in.name, exclude_id=db_tag.id)
                if existing_tag:
                    raise ValueError(f"タグ名 '{tag_in.name}' は既に使用されています")

            # タグ更新
            update_data = tag_in.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_tag, field, value)

            await db.commit()
            await db.refresh(db_tag)

            return db_tag

        except Exception as e:
            await db.rollback()
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"ユーザータグ更新エラー: {e}")
            raise

    async def soft_delete(self, db: AsyncSession, *, db_tag: Tag) -> Tag:
        """ソフトデリート（論理削除）"""
        try:
            db_tag.is_active = False
            await db.commit()
            await db.refresh(db_tag)
            return db_tag

        except Exception as e:
            await db.rollback()
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"タグソフトデリートエラー: {e}")
            raise

    def _apply_filters(self, stmt: Any, filters: TagFilters) -> Any:
        """フィルタリング条件を適用"""
        if filters.is_active is not None:
            stmt = stmt.where(self.model.is_active == filters.is_active)

        if filters.colors:
            stmt = stmt.where(self.model.color.in_(filters.colors))

        if filters.has_tasks is not None:
            if filters.has_tasks:
                # タスクがあるタグのみ
                stmt = stmt.join(TaskTag, self.model.id == TaskTag.tag_id)
            else:
                # タスクがないタグのみ
                stmt = stmt.outerjoin(TaskTag, self.model.id == TaskTag.tag_id)
                stmt = stmt.where(TaskTag.id.is_(None))

        if filters.min_task_count is not None:
            stmt = (
                stmt.outerjoin(TaskTag, self.model.id == TaskTag.tag_id)
                .group_by(self.model.id)
                .having(func.count(TaskTag.id) >= filters.min_task_count)
            )

        if filters.search:
            search_term = f"%{filters.search}%"
            stmt = stmt.where(or_(self.model.name.ilike(search_term), self.model.description.ilike(search_term)))

        return stmt

    def _apply_sort(self, stmt: Any, sort_options: TagSortOptions) -> Any:
        """ソート条件を適用"""
        sort_field = getattr(self.model, sort_options.sort_by, None)
        if sort_field is None:
            # フィールドが存在しない場合はデフォルトソート
            return stmt.order_by(self.model.created_at.desc())

        if sort_options.order == "desc":
            return stmt.order_by(sort_field.desc())
        else:
            return stmt.order_by(sort_field.asc())


tag_crud = CRUDTag(Tag)
