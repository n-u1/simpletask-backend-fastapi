"""タグリポジトリ

タグデータアクセス層の抽象化
"""

import uuid
from abc import ABC, abstractmethod

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.core.constants import APIConstants
from app.dtos.tag import TagDTO, TagListDTO, TagSummaryDTO
from app.models.tag import Tag
from app.models.task import Task
from app.models.task_tag import TaskTag
from app.schemas.tag import TagFilters, TagSortOptions


class TagRepositoryInterface(ABC):
    """タグリポジトリのインターフェース"""

    @abstractmethod
    async def get_by_id(self, db: AsyncSession, tag_id: uuid.UUID, user_id: uuid.UUID) -> TagDTO | None:
        """IDでタグを取得"""
        pass

    @abstractmethod
    async def get_list(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = APIConstants.DEFAULT_PAGE_SIZE,
        filters: TagFilters | None = None,
        sort_options: TagSortOptions | None = None,
        include_inactive: bool = False,
    ) -> TagListDTO:
        """ユーザーのタグ一覧を取得"""
        pass

    @abstractmethod
    async def get_summary_by_ids(
        self, db: AsyncSession, tag_ids: list[uuid.UUID], user_id: uuid.UUID
    ) -> list[TagSummaryDTO]:
        """指定IDのタグ要約情報を取得"""
        pass


class TagRepository(TagRepositoryInterface):
    """タグリポジトリの実装"""

    async def get_by_id(self, db: AsyncSession, tag_id: uuid.UUID, user_id: uuid.UUID) -> TagDTO | None:
        """IDでタグを取得"""
        # タグの基本情報を取得
        stmt = select(Tag).where(Tag.id == tag_id, Tag.user_id == user_id)
        result = await db.execute(stmt)
        tag = result.scalar_one_or_none()

        if not tag:
            return None

        # タスク数の集計をSQLで実行
        task_counts = await self._get_task_counts_for_tag(db, tag_id)

        # DTOに変換（セッション内）
        return TagDTO(
            id=tag.id,
            user_id=tag.user_id,
            name=tag.name,
            color=tag.color,
            description=tag.description,
            is_active=tag.is_active,
            created_at=tag.created_at,
            updated_at=tag.updated_at,
            task_count=task_counts["total"],
            active_task_count=task_counts["active"],
            completed_task_count=task_counts["completed"],
        )

    async def get_list(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = APIConstants.DEFAULT_PAGE_SIZE,
        filters: TagFilters | None = None,
        sort_options: TagSortOptions | None = None,
        include_inactive: bool = False,
    ) -> TagListDTO:
        """ユーザーのタグ一覧を取得

        パフォーマンスを考慮してバッチ処理で実装
        """
        # ベースクエリ構築
        stmt = select(Tag).where(Tag.user_id == user_id)

        # アクティブ状態フィルタ
        if not include_inactive:
            stmt = stmt.where(Tag.is_active == True)  # noqa: E712

        # フィルタリング適用
        if filters:
            stmt = self._apply_filters(stmt, filters)

        # ソート適用
        stmt = self._apply_sort(stmt, sort_options) if sort_options else stmt.order_by(Tag.created_at.desc())

        # 総件数取得（ページネーション用）
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        # ページネーション適用
        stmt = stmt.offset(skip).limit(limit)

        # タグ取得
        result = await db.execute(stmt)
        tags = list(result.scalars().all())

        if not tags:
            return TagListDTO(
                tags=[],
                total=0,
                page=(skip // limit) + 1,
                per_page=limit,
                total_pages=0,
            )

        # 全タグのタスク数を効率的に取得
        tag_ids = [tag.id for tag in tags]
        task_counts_map = await self._get_task_counts_for_tags(db, tag_ids)

        # DTOに変換
        tag_dtos = []
        for tag in tags:
            counts = task_counts_map.get(tag.id, {"total": 0, "active": 0, "completed": 0})
            tag_dto = TagDTO(
                id=tag.id,
                user_id=tag.user_id,
                name=tag.name,
                color=tag.color,
                description=tag.description,
                is_active=tag.is_active,
                created_at=tag.created_at,
                updated_at=tag.updated_at,
                task_count=counts["total"],
                active_task_count=counts["active"],
                completed_task_count=counts["completed"],
            )
            tag_dtos.append(tag_dto)

        # ページネーション情報計算
        page = (skip // limit) + 1
        total_pages = (total + limit - 1) // limit

        return TagListDTO(
            tags=tag_dtos,
            total=total,
            page=page,
            per_page=limit,
            total_pages=total_pages,
        )

    async def get_summary_by_ids(
        self, db: AsyncSession, tag_ids: list[uuid.UUID], user_id: uuid.UUID
    ) -> list[TagSummaryDTO]:
        """指定IDのタグ要約情報を取得

        TaskDTOなどで使用する軽量なタグ情報
        """
        if not tag_ids:
            return []

        stmt = (
            select(Tag)
            .where(Tag.id.in_(tag_ids), Tag.user_id == user_id, Tag.is_active == True)  # noqa: E712
            .order_by(Tag.name)
        )

        result = await db.execute(stmt)
        tags = list(result.scalars().all())

        return [
            TagSummaryDTO(
                id=tag.id,
                name=tag.name,
                color=tag.color,
                description=tag.description,
            )
            for tag in tags
        ]

    async def _get_task_counts_for_tag(self, db: AsyncSession, tag_id: uuid.UUID) -> dict[str, int]:
        """単一タグのタスク数を効率的に取得"""
        # 総タスク数
        total_stmt = (
            select(func.count(Task.id))
            .select_from(TaskTag)
            .join(Task, TaskTag.task_id == Task.id)
            .where(TaskTag.tag_id == tag_id)
        )

        # アクティブタスク数（archived以外）
        active_stmt = (
            select(func.count(Task.id))
            .select_from(TaskTag)
            .join(Task, TaskTag.task_id == Task.id)
            .where(TaskTag.tag_id == tag_id, Task.status != "archived")
        )

        # 完了タスク数
        completed_stmt = (
            select(func.count(Task.id))
            .select_from(TaskTag)
            .join(Task, TaskTag.task_id == Task.id)
            .where(TaskTag.tag_id == tag_id, Task.status == "done")
        )

        total_result = await db.execute(total_stmt)
        active_result = await db.execute(active_stmt)
        completed_result = await db.execute(completed_stmt)

        # scalar()の結果はintかNoneなので、0でデフォルト値を設定
        return {
            "total": total_result.scalar() or 0,
            "active": active_result.scalar() or 0,
            "completed": completed_result.scalar() or 0,
        }

    async def _get_task_counts_for_tags(
        self, db: AsyncSession, tag_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, dict[str, int]]:
        """複数タグのタスク数を効率的にバッチ取得"""
        if not tag_ids:
            return {}

        # 総タスク数
        total_stmt = (
            select(TaskTag.tag_id, func.count(Task.id).label("total_count"))
            .select_from(TaskTag)
            .join(Task, TaskTag.task_id == Task.id)
            .where(TaskTag.tag_id.in_(tag_ids))
            .group_by(TaskTag.tag_id)
        )

        # アクティブタスク数（archived以外）
        active_stmt = (
            select(TaskTag.tag_id, func.count(Task.id).label("active_count"))
            .select_from(TaskTag)
            .join(Task, TaskTag.task_id == Task.id)
            .where(TaskTag.tag_id.in_(tag_ids), Task.status != "archived")
            .group_by(TaskTag.tag_id)
        )

        # 完了タスク数
        completed_stmt = (
            select(TaskTag.tag_id, func.count(Task.id).label("completed_count"))
            .select_from(TaskTag)
            .join(Task, TaskTag.task_id == Task.id)
            .where(TaskTag.tag_id.in_(tag_ids), Task.status == "done")
            .group_by(TaskTag.tag_id)
        )

        # 結果を取得
        total_result = await db.execute(total_stmt)
        active_result = await db.execute(active_stmt)
        completed_result = await db.execute(completed_stmt)

        # 結果をマップに変換
        total_map: dict[uuid.UUID, int] = {}
        for row in total_result.all():
            total_map[row.tag_id] = row.total_count or 0

        active_map: dict[uuid.UUID, int] = {}
        for row in active_result.all():
            active_map[row.tag_id] = row.active_count or 0

        completed_map: dict[uuid.UUID, int] = {}
        for row in completed_result.all():
            completed_map[row.tag_id] = row.completed_count or 0

        # 最終的なマップを構築
        counts_map: dict[uuid.UUID, dict[str, int]] = {}
        for tag_id in tag_ids:
            counts_map[tag_id] = {
                "total": total_map.get(tag_id, 0),
                "active": active_map.get(tag_id, 0),
                "completed": completed_map.get(tag_id, 0),
            }

        return counts_map

    def _apply_filters(self, stmt: Select[tuple[Tag]], filters: TagFilters) -> Select[tuple[Tag]]:
        """フィルタリング条件を適用"""
        if filters.is_active is not None:
            stmt = stmt.where(Tag.is_active == filters.is_active)

        if filters.colors:
            stmt = stmt.where(Tag.color.in_(filters.colors))

        if filters.has_tasks is not None:
            if filters.has_tasks:
                stmt = stmt.join(TaskTag, Tag.id == TaskTag.tag_id)
            else:
                stmt = stmt.outerjoin(TaskTag, Tag.id == TaskTag.tag_id)
                stmt = stmt.where(TaskTag.id.is_(None))

        if filters.min_task_count is not None:
            stmt = (
                stmt.outerjoin(TaskTag, Tag.id == TaskTag.tag_id)
                .group_by(Tag.id)
                .having(func.count(TaskTag.id) >= filters.min_task_count)
            )

        if filters.search:
            search_term = f"%{filters.search}%"
            stmt = stmt.where(Tag.name.ilike(search_term) | Tag.description.ilike(search_term))

        return stmt

    def _apply_sort(self, stmt: Select[tuple[Tag]], sort_options: TagSortOptions) -> Select[tuple[Tag]]:
        """ソート条件を適用"""
        sort_field = getattr(Tag, sort_options.sort_by, None)
        if sort_field is None:
            # フィールドが存在しない場合はデフォルトソート
            return stmt.order_by(Tag.created_at.desc())

        if sort_options.order == "desc":
            return stmt.order_by(sort_field.desc())
        else:
            return stmt.order_by(sort_field.asc())


# シングルトンインスタンス
tag_repository = TagRepository()
