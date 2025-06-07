"""データベース接続管理モジュール

SQLAlchemy 2.x + asyncpgを使用したPostgreSQL接続の管理、
非同期セッション、接続プール、ヘルスチェック機能を提供
"""

import logging
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, Pool, QueuePool

from app.core.config import settings

logger = logging.getLogger(__name__)


# ======================================
# 1. カスタム例外クラスを追加
# ======================================


class DatabaseConnectionError(Exception):
    """データベース接続関連のエラー"""

    pass


class DatabaseConfigurationError(Exception):
    """データベース設定関連のエラー"""

    pass


class DatabaseManager:
    """データベース接続を管理するクラス

    SQLAlchemy 2.x準拠の非同期エンジンとセッション管理を提供
    シングルトンパターンで全体共有
    """

    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    def create_engine(self) -> AsyncEngine:
        """非同期SQLAlchemyエンジンを作成"""
        if self._engine is not None:
            return self._engine

        # 接続プールの設定
        pool_class: type[Pool] = QueuePool
        pool_kwargs = {
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_timeout": 30,
            "pool_recycle": 3600,  # 1時間でコネクションを再作成
            "pool_pre_ping": True,  # 接続確認
        }

        # 開発環境ではNullPoolを使用（デバッグがしやすいため）
        if settings.is_development:
            pool_class = NullPool
            pool_kwargs = {}

        # エンジン作成設定
        engine_kwargs = {
            "poolclass": pool_class,
            "echo": settings.is_development,
            "echo_pool": settings.is_development,
            "future": True,
            "connect_args": {
                "server_settings": {
                    "application_name": f"{settings.PROJECT_NAME}-{settings.ENVIRONMENT}",
                    "timezone": "UTC",
                }
            },
            **pool_kwargs,
        }

        try:
            self._engine = create_async_engine(settings.database_url_async, **engine_kwargs)
            logger.info(f"データベースエンジンが作成されました: {settings.DB_HOST}:{settings.DB_PORT}")
            return self._engine

        except Exception as e:
            logger.error(f"データベースエンジンの作成に失敗しました: {e}")
            raise

    def create_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """非同期セッションファクトリーを作成"""
        if self._session_factory is not None:
            return self._session_factory

        if self._engine is None:
            self.create_engine()

        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,  # コミット後もオブジェクトを使用可能
            autoflush=True,
            autocommit=False,
        )

        logger.info("データベースセッションファクトリーが作成されました")
        return self._session_factory

    async def get_session(self) -> AsyncGenerator[AsyncSession]:
        """データベースセッションを取得（依存性注入用）。

        Yields:
            非同期データベースセッション

        Example:
            from fastapi import Depends

            async def get_user(db: AsyncSession = Depends(get_db)):
                # セッションを使用
                pass
        """
        if self._session_factory is None:
            self.create_session_factory()

        # 修正: assert文を適切な例外処理に変更
        if self._session_factory is None:
            raise DatabaseConnectionError("セッションファクトリが初期化されていません")

        async with self._session_factory() as session:
            try:
                logger.debug("データベースセッションを作成しました")
                yield session
            except Exception as e:
                logger.error(f"セッション使用中にエラーが発生しました: {e}")
                await session.rollback()
                raise
            finally:
                await session.close()
                logger.debug("データベースセッションを閉じました")

    async def check_connection(self) -> bool:
        """データベース接続の健全性をチェック

        Returns:
            接続が正常な場合True、それ以外False
        """
        try:
            if self._engine is None:
                self.create_engine()

            # 修正: assert文を適切な例外処理に変更
            if self._engine is None:
                raise DatabaseConnectionError("データベースエンジンが初期化されていません")

            async with self._engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                result.scalar()

            logger.info("データベース接続チェック: 正常")
            return True

        except SQLAlchemyError as e:
            logger.error(f"データベース接続チェック失敗: {e}")
            return False
        except Exception as e:
            logger.error(f"データベース接続チェック中に予期しないエラー: {e}")
            return False

    async def close(self) -> None:
        """データベースエンジンとセッションを終了

        アプリケーション終了時に呼び出す
        """
        if self._engine is not None:
            await self._engine.dispose()
            logger.info("データベースエンジンを閉じました")
            self._engine = None
            self._session_factory = None

    @property
    def engine(self) -> AsyncEngine | None:
        """現在のエンジンインスタンスを取得"""
        return self._engine

    @property
    def is_connected(self) -> bool:
        """エンジンが作成済みかどうかを確認"""
        return self._engine is not None


# グローバルデータベースマネージャーインスタンス
database_manager = DatabaseManager()


async def get_db() -> AsyncGenerator[AsyncSession]:
    """FastAPI依存性注入用のデータベースセッション取得関数

    Yields:
        非同期データベースセッション

    Example:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            # データベース操作
            pass
    """
    async for session in database_manager.get_session():
        yield session


# テーブル管理関数
async def create_tables() -> None:
    """すべてのテーブルを作成（開発・テスト用）

    注意: 本番環境ではAlembicマイグレーションを使用
    """
    try:
        # ベースモデルをインポート（循環インポート回避のため遅延インポート）
        try:
            from app.models.base import Base
        except ImportError as err:
            logger.warning("app.models.baseが見つかりません。")
            raise RuntimeError("ベースモデルが見つかりません。") from err

        engine = database_manager.create_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("すべてのテーブルが作成されました")

    except Exception as e:
        logger.error(f"テーブル作成中にエラーが発生しました: {e}")
        raise


async def drop_tables() -> None:
    """すべてのテーブルを削除（テスト用）

    注意: 絶対にテスト環境でのみ使用のこと
    """
    if not settings.is_testing:
        raise RuntimeError("drop_tables()はテスト環境でのみ実行可能です")

    try:
        # ベースモデルをインポート（循環インポート回避のため遅延インポート）
        try:
            from app.models.base import Base
        except ImportError as err:
            logger.warning("app.models.baseが見つかりません。")
            raise RuntimeError("ベースモデルが見つかりません。") from err

        engine = database_manager.create_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

        logger.warning("すべてのテーブルが削除されました")

    except Exception as e:
        logger.error(f"テーブル削除中にエラーが発生しました: {e}")
        raise


# アプリケーションライフサイクル管理
async def init_database() -> None:
    try:
        # エンジンとセッションファクトリーを初期化
        database_manager.create_engine()
        database_manager.create_session_factory()

        # 接続テスト
        is_connected = await database_manager.check_connection()
        if not is_connected:
            raise RuntimeError("データベースへの接続に失敗しました")

        logger.info("データベースの初期化が完了しました")

    except Exception as e:
        logger.error(f"データベース初期化中にエラーが発生しました: {e}")
        raise


async def close_database() -> None:
    """データベース接続を終了"""
    try:
        await database_manager.close()
        logger.info("データベース接続を正常に閉じました")

    except Exception as e:
        logger.error(f"データベース接続の終了中にエラーが発生しました: {e}")


async def health_check() -> dict:
    """データベースのヘルスチェックを実行

    Returns:
        ヘルスチェック結果を含む辞書

    Example:
        result = await health_check()
        print(result["status"])  # "healthy" or "unhealthy"
    """
    try:
        is_connected = await database_manager.check_connection()

        if is_connected:
            return {
                "status": "healthy",
                "database": "connected",
                "host": settings.DB_HOST,
                "port": settings.DB_PORT,
                "database_name": settings.DB_NAME,
            }
        else:
            return {
                "status": "unhealthy",
                "database": "disconnected",
                "error": "Connection failed",
            }

    except Exception as e:
        logger.error(f"ヘルスチェック中にエラーが発生しました: {e}")
        return {
            "status": "unhealthy",
            "database": "error",
            "error": str(e),
        }


# トランザクション管理ユーティリティ
class DatabaseTransaction:
    """データベーストランザクションを管理するコンテキストマネージャー

    Example:
        async with DatabaseTransaction() as session:
            # トランザクション内での操作
            user = User(name="test")
            session.add(user)
            # 正常終了時に自動コミット、例外時に自動ロールバック
    """

    def __init__(self) -> None:
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> AsyncSession:
        """トランザクションを開始"""
        if database_manager._session_factory is None:
            database_manager.create_session_factory()

        # 修正: assert文を適切な例外処理に変更
        if database_manager._session_factory is None:
            raise DatabaseConnectionError("セッションファクトリが初期化されていません")

        self.session = database_manager._session_factory()
        return self.session

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any | None,
    ) -> None:
        """トランザクションを終了します。"""
        if self.session is None:
            return

        try:
            if exc_type is None:
                # 例外が発生していない場合はコミット
                await self.session.commit()
                logger.debug("トランザクションをコミットしました")
            else:
                # 例外が発生した場合はロールバック
                await self.session.rollback()
                logger.warning(f"トランザクションをロールバックしました: {exc_val}")
        finally:
            await self.session.close()
            logger.debug("トランザクションセッションを閉じました")


# 使用例とテスト用ユーティリティ
async def test_database_operations() -> None:
    """データベース操作のテスト関数（開発用）。

    基本的なCRUD操作をテスト
    """
    if not settings.is_development:
        raise RuntimeError("この関数は開発環境でのみ実行可能です")

    try:
        logger.info("データベース操作テストを開始します")

        # 接続テスト
        is_connected = await database_manager.check_connection()
        # 修正: assert文を適切な例外処理に変更
        if not is_connected:
            raise DatabaseConnectionError("データベース接続に失敗しました")

        # セッションテスト
        async for session in database_manager.get_session():
            result = await session.execute(text("SELECT current_timestamp"))
            timestamp = result.scalar()
            logger.info(f"現在時刻: {timestamp}")
            break

        # トランザクションテスト
        async with DatabaseTransaction() as session:
            result = await session.execute(text("SELECT version()"))
            version = result.scalar()
            logger.info(f"PostgreSQLバージョン: {version}")

        logger.info("データベース操作テストが正常に完了しました")

    except DatabaseConnectionError as e:
        logger.error(f"データベース操作テスト中にエラーが発生しました: {e}")
        raise
    except Exception as e:
        logger.error(f"データベース操作テスト中に予期しないエラーが発生しました: {e}")
        raise DatabaseConnectionError(f"予期しないエラー: {e}") from e


if __name__ == "__main__":
    import asyncio

    async def main() -> None:
        """開発用メイン関数"""
        logging.basicConfig(level=logging.INFO)

        try:
            await init_database()

            health = await health_check()
            print(f"ヘルスチェック結果: {health}")

            await test_database_operations()

        finally:
            await close_database()

    asyncio.run(main())
