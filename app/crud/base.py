"""ベースCRUDクラス

全てのCRUD操作の基底クラスを提供
"""

from typing import TYPE_CHECKING, Any, Generic, TypeVar
from uuid import UUID

if TYPE_CHECKING:
    from collections.abc import Sequence

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base
from app.utils.error_handler import handle_db_operation

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """ベースCRUDクラス

    基本的なCRUD操作を提供
    すべてのCRUDクラスはこのクラスを継承する
    """

    def __init__(self, model: type[ModelType]):
        """Args:

        model: SQLAlchemyモデルクラス
        """
        self.model = model

    @handle_db_operation("レコード取得")
    async def get(self, db: AsyncSession, id: UUID | str) -> ModelType | None:
        """IDでレコードを取得

        Args:
            db: データベースセッション
            id: レコードID

        Returns:
            見つかった場合はモデルインスタンス、見つからない場合はNone
        """
        stmt = select(self.model).where(self.model.id == id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @handle_db_operation("複数レコード取得")
    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100, order_by: str | None = None, desc: bool = False
    ) -> list[ModelType]:
        """複数レコードを取得

        Args:
            db: データベースセッション
            skip: スキップする件数
            limit: 取得する最大件数
            order_by: ソート対象フィールド名
            desc: 降順ソートフラグ

        Returns:
            モデルインスタンスのリスト
        """
        stmt = select(self.model)

        if order_by:
            if hasattr(self.model, order_by):
                order_column = getattr(self.model, order_by)
                stmt = stmt.order_by(order_column.desc() if desc else order_column)
            else:
                # デフォルトソート（作成日時降順）
                stmt = stmt.order_by(self.model.created_at.desc())
        else:
            stmt = stmt.order_by(self.model.created_at.desc())

        # ページネーション
        stmt = stmt.offset(skip).limit(limit)

        result = await db.execute(stmt)
        users: Sequence[ModelType] = result.scalars().all()
        return list(users)

    @handle_db_operation("レコード数取得")
    async def count(self, db: AsyncSession) -> int:
        """総レコード数を取得

        Args:
            db: データベースセッション

        Returns:
            総レコード数
        """
        stmt = select(func.count(self.model.id))
        result = await db.execute(stmt)
        return result.scalar() or 0

    @handle_db_operation("レコード作成")
    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType | dict[str, Any]) -> ModelType:
        """新しいレコードを作成

        Args:
            db: データベースセッション
            obj_in: 作成データ（PydanticモデルまたはDict）

        Returns:
            作成されたモデルインスタンス

        Raises:
            Exception: データベースエラーの場合
        """
        # Pydanticモデルの場合は辞書に変換
        obj_in_data = obj_in if isinstance(obj_in, dict) else jsonable_encoder(obj_in)

        # SQLAlchemyモデルインスタンス作成
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @handle_db_operation("レコード更新")
    async def update(
        self, db: AsyncSession, *, db_obj: ModelType, obj_in: UpdateSchemaType | dict[str, Any]
    ) -> ModelType:
        """既存レコードを更新

        Args:
            db: データベースセッション
            db_obj: 更新対象のモデルインスタンス
            obj_in: 更新データ（PydanticモデルまたはDict）

        Returns:
            更新されたモデルインスタンス

        Raises:
            Exception: データベースエラーの場合
        """
        # 更新データの準備
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)

        # None値や空文字列の除外
        update_data = {k: v for k, v in update_data.items() if v is not None}

        # モデルインスタンスの更新
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @handle_db_operation("レコード削除")
    async def delete(self, db: AsyncSession, *, id: UUID | str) -> ModelType | None:
        """レコードを削除

        Args:
            db: データベースセッション
            id: 削除対象のレコードID

        Returns:
            削除されたモデルインスタンス、見つからない場合はNone

        Raises:
            Exception: データベースエラーの場合
        """
        # 対象レコードを取得
        obj = await self.get(db, id=id)
        if obj is None:
            return None

        # 削除前にオブジェクトの情報を保存（型安全性のため）
        deleted_obj: ModelType = obj

        # 削除実行
        await db.delete(obj)
        await db.commit()

        return deleted_obj

    @handle_db_operation("レコード存在確認")
    async def exists(self, db: AsyncSession, id: UUID | str) -> bool:
        """レコードの存在確認

        Args:
            db: データベースセッション
            id: 確認対象のレコードID

        Returns:
            存在する場合True、しない場合False
        """
        stmt = select(self.model.id).where(self.model.id == id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    # バルク操作
    @handle_db_operation("複数レコード作成")
    async def create_multi(
        self, db: AsyncSession, *, obj_list: list[CreateSchemaType | dict[str, Any]]
    ) -> list[ModelType]:
        """複数レコードを一括作成

        Args:
            db: データベースセッション
            obj_list: 作成データのリスト

        Returns:
            作成されたモデルインスタンスのリスト

        Raises:
            Exception: データベースエラーの場合
        """
        db_objects = []

        for obj_in in obj_list:
            obj_in_data = obj_in if isinstance(obj_in, dict) else jsonable_encoder(obj_in)

            db_obj = self.model(**obj_in_data)
            db_objects.append(db_obj)

        db.add_all(db_objects)
        await db.commit()

        # 全オブジェクトをリフレッシュ
        for db_obj in db_objects:
            await db.refresh(db_obj)

        return list(db_objects)

    @handle_db_operation("複数レコード削除")
    async def delete_multi(self, db: AsyncSession, *, ids: list[UUID | str]) -> int:
        """複数レコードを一括削除

        Args:
            db: データベースセッション
            ids: 削除対象のレコードIDリスト

        Returns:
            削除されたレコード数

        Raises:
            Exception: データベースエラーの場合
        """
        stmt = delete(self.model).where(self.model.id.in_(ids))
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount
