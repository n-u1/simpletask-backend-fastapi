"""テスト用モック設定"""

from unittest.mock import AsyncMock, MagicMock


def setup_redis_mock() -> None:
    """Redisモック化を実行"""
    try:
        import app.core.redis as redis_module

        # キャッシュモック
        redis_module.cache = MagicMock()
        redis_module.cache.get = AsyncMock(return_value=None)
        redis_module.cache.set = AsyncMock(return_value=True)
        redis_module.cache.exists = AsyncMock(return_value=False)
        redis_module.cache.delete = AsyncMock(return_value=True)

        # レート制限モック
        redis_module.rate_limiter = MagicMock()
        redis_module.rate_limiter.is_allowed = AsyncMock(return_value=True)
        redis_module.rate_limiter.get_remaining = AsyncMock(return_value={"reset_time": 0})

        print("✅ Redis モック化完了")

    except ImportError as e:
        print(f"⚠️ Redis モジュールが見つかりません: {e}")
