"""pytest設定とテスト環境インフラ

基本的なフィクスチャとテスト設定のエントリーポイント
"""

import os
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from tests.fixtures.auth import *  # noqa: F403, F401
from tests.fixtures.entities import *  # noqa: F403, F401
from tests.fixtures.sample_data import *  # noqa: F403, F401
from tests.tests_config.app_factory import create_test_app
from tests.tests_config.database import get_test_db_session
from tests.tests_config.mocks import setup_redis_mock


@pytest.fixture(scope="session", autouse=True)
def setup_test_env() -> None:
    """テスト環境セットアップ"""
    # 環境変数設定
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["DB_NAME"] = "test_simpletask"
    os.environ["LOG_LEVEL"] = "WARNING"

    print(f"✅ 環境変数設定完了: ENVIRONMENT={os.environ.get('ENVIRONMENT')}")

    # 設定モジュールをリロード
    _reload_config_module()

    # Redisモック化
    setup_redis_mock()


def _reload_config_module() -> None:
    """設定モジュールを強制的にリロード"""
    try:
        import importlib
        import sys

        if "app.core.config" in sys.modules:
            importlib.reload(sys.modules["app.core.config"])
            print("✅ 設定モジュールリロード完了")

        import app.core.config as config_module

        if hasattr(config_module, "_settings_instance"):
            config_module._settings_instance = None
            print("✅ 設定インスタンスクリア完了")

        from app.core.config import get_settings

        test_settings = get_settings()
        print(f"✅ 新設定確認: ENVIRONMENT={test_settings.ENVIRONMENT}, is_testing={test_settings.is_testing}")

    except Exception as e:
        print(f"⚠️ 設定リセットエラー: {e}")


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    """テスト用データベースセッション"""
    async for session in get_test_db_session():
        yield session


@pytest.fixture
def client(db_session: AsyncSession) -> Generator[TestClient]:
    """テスト用同期HTTPクライアント"""
    app = create_test_app()

    def override_get_db() -> Generator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """テスト用非同期HTTPクライアント"""
    app = create_test_app()

    def override_get_db() -> Generator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client
    finally:
        app.dependency_overrides.clear()
