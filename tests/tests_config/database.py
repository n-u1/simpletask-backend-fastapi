"""テスト用データベース設定"""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.base import Base

# テスト用データベース設定
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# テスト用エンジン
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
    echo=False,
)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
    """SQLiteの外部キー制約を有効化"""
    if "sqlite" in str(dbapi_connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


async def get_test_db_session() -> AsyncGenerator[AsyncSession]:
    """テスト用データベースセッションを作成"""
    # テーブル作成
    async with test_engine.begin() as conn:
        await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.run_sync(Base.metadata.create_all)

    # セッション作成
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        await session.execute(text("PRAGMA foreign_keys=ON"))
        await session.commit()
        yield session

    # テーブル削除
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
