"""Redis接続管理モジュール

Redisクライアントの接続管理、キャッシュ機能、セッション管理、レート制限機能を提供
"""

import json
import logging
from typing import Any, cast

from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import ConnectionError, RedisError, TimeoutError

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisManager:
    """Redis接続を管理するクラス

    非同期Redis操作、接続プール管理、キャッシュ機能を提供
    シングルトンパターンで全体共有
    """

    def __init__(self) -> None:
        self._client: Redis | None = None
        self._pool: ConnectionPool | None = None

    def create_connection_pool(self) -> ConnectionPool:
        if self._pool is not None:
            return self._pool

        self._validate_redis_settings()

        try:
            self._pool = ConnectionPool(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                encoding="utf-8",
                decode_responses=True,
                max_connections=settings.REDIS_POOL_SIZE,
                retry_on_timeout=True,
                health_check_interval=settings.REDIS_HEALTH_CHECK_INTERVAL,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT_DEV
                if settings.is_development
                else settings.REDIS_SOCKET_TIMEOUT_PROD,
                socket_connect_timeout=settings.REDIS_SOCKET_TIMEOUT_DEV
                if settings.is_development
                else settings.REDIS_SOCKET_TIMEOUT_PROD,
            )
            logger.info(f"Redis接続プールが作成されました: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            return self._pool

        except Exception as e:
            logger.error(f"Redis接続プールの作成に失敗しました: {e}")
            raise

    def _validate_redis_settings(self) -> None:
        """Redis設定の検証"""
        if not settings.REDIS_HOST or not settings.REDIS_HOST.strip():
            raise ValueError("REDIS_HOSTが設定されていません")

        if not (settings.REDIS_PORT_MIN <= settings.REDIS_PORT <= settings.REDIS_PORT_MAX):
            raise ValueError(
                f"REDIS_PORTは{settings.REDIS_PORT_MIN}-{settings.REDIS_PORT_MAX}の範囲で設定してください: "
                f"{settings.REDIS_PORT}"
            )

        if not (settings.REDIS_DB_MIN <= settings.REDIS_DB <= settings.REDIS_DB_MAX):
            raise ValueError(
                f"REDIS_DBは{settings.REDIS_DB_MIN}-{settings.REDIS_DB_MAX}の"
                f"範囲で設定してください: {settings.REDIS_DB}"
            )

        if not settings.REDIS_PASSWORD:
            raise ValueError("REDIS_PASSWORDが設定されていません")

        if not (settings.REDIS_POOL_SIZE_MIN <= settings.REDIS_POOL_SIZE <= settings.REDIS_POOL_SIZE_MAX):
            raise ValueError(
                f"REDIS_POOL_SIZEは{settings.REDIS_POOL_SIZE_MIN}-{settings.REDIS_POOL_SIZE_MAX}の"
                f"範囲で設定してください: {settings.REDIS_POOL_SIZE}"
            )

        if settings.is_production:
            if settings.REDIS_HOST in ["localhost", "127.0.0.1"]:
                logger.warning("本番環境でlocalhostのRedisを使用しています")

            if len(settings.REDIS_PASSWORD) < settings.MIN_REDIS_PASSWORD_LENGTH_PRODUCTION:
                raise ValueError(
                    f"本番環境ではREDIS_PASSWORDは{settings.MIN_REDIS_PASSWORD_LENGTH_PRODUCTION}文字以上にしてください"
                )

        logger.debug("Redis設定の検証が完了しました")

    async def ping(self) -> bool:
        """Redisの接続チェック"""
        try:
            if self._client is None:
                self.create_client()

            assert self._client is not None
            await self._client.ping()
            logger.debug("Redis接続チェック: 正常")
            return True

        except (ConnectionError, TimeoutError, RedisError) as e:
            logger.error(f"Redis接続チェック失敗: {e}")
            return False
        except Exception as e:
            logger.error(f"Redis接続チェック中に予期しないエラー: {e}")
            return False

    def create_client(self) -> Redis:
        if self._client is not None:
            return self._client

        if self._pool is None:
            self.create_connection_pool()

        try:
            assert self._pool is not None
            self._client = Redis(connection_pool=self._pool)
            logger.info("Redisクライアントが作成されました")
            return self._client

        except Exception as e:
            logger.error(f"Redisクライアントの作成に失敗しました: {e}")
            raise

    async def close(self) -> None:
        try:
            if self._client is not None:
                await self._client.aclose()  # type: ignore[attr-defined]
                logger.info("Redisクライアントを閉じました")
                self._client = None

            if self._pool is not None:
                await self._pool.aclose()  # type: ignore[attr-defined]
                logger.info("Redis接続プールを閉じました")
                self._pool = None

        except Exception as e:
            logger.error(f"Redis接続の終了中にエラーが発生しました: {e}")

    @property
    def client(self) -> Redis | None:
        """現在のRedisクライアントインスタンスを取得"""
        return self._client

    @property
    def is_connected(self) -> bool:
        """クライアントが作成済みかどうかを確認"""
        return self._client is not None


_redis_manager_instance: RedisManager | None = None


def get_redis_manager() -> RedisManager:
    """シングルトンパターンでRedisManagerインスタンスを取得"""
    global _redis_manager_instance

    if _redis_manager_instance is None:
        _redis_manager_instance = RedisManager()
        logger.info("RedisManagerシングルトンインスタンスを作成しました")

    return _redis_manager_instance


def reset_redis_manager() -> None:
    """シングルトンインスタンスのリセット（主にテスト用）"""
    global _redis_manager_instance
    _redis_manager_instance = None


# グローバルRedisマネージャーインスタンス
redis_manager = get_redis_manager()


# Redis操作ユーティリティクラス
class RedisCache:
    """Redisキャッシュ操作を提供するクラス"""

    def __init__(self, manager: RedisManager | None = None) -> None:
        self._manager = manager

    @property
    def manager(self) -> RedisManager:
        """RedisManagerを取得"""
        if self._manager is not None:
            return self._manager
        return get_redis_manager()

    @property
    def client(self) -> Redis:
        """Redisクライアントを取得"""
        manager = self.manager
        if manager.client is None:
            manager.create_client()

        assert manager.client is not None
        return manager.client

    async def get(self, key: str) -> str | None:
        """キーから値を取得"""
        try:
            value = await self.client.get(key)
            if value is not None:
                logger.debug(f"キャッシュヒット: {key}")
                return cast("str", value)  # decode_responses=True なので str
            return None
        except RedisError as e:
            logger.error(f"キャッシュ取得エラー: {key}, {e}")
            return None

    async def set(self, key: str, value: str, expire: int | None = None) -> bool:
        """キーと値を設定（有効期限は単位が秒）"""
        try:
            result = await self.client.set(key, value, ex=expire)
            logger.debug(f"キャッシュ設定: {key}, expire={expire}")
            return bool(result)
        except RedisError as e:
            logger.error(f"キャッシュ設定エラー: {key}, {e}")
            return False

    async def delete(self, key: str) -> bool:
        """キーを削除"""
        try:
            result = await self.client.delete(key)
            logger.debug(f"キャッシュ削除: {key}")
            return bool(result)
        except RedisError as e:
            logger.error(f"キャッシュ削除エラー: {key}, {e}")
            return False

    async def exists(self, key: str) -> bool:
        """キーの存在チェック"""
        try:
            result = await self.client.exists(key)
            return bool(result)
        except RedisError as e:
            logger.error(f"キー存在チェックエラー: {key}, {e}")
            return False

    async def expire(self, key: str, seconds: int) -> bool:
        """キーに有効期限を設定"""
        try:
            result = await self.client.expire(key, seconds)
            return bool(result)
        except RedisError as e:
            logger.error(f"有効期限設定エラー: {key}, {e}")
            return False

    async def ttl(self, key: str) -> int:
        """キーの残り有効期限を取得

        Args:
            key: 対象キー

        Returns:
            残り秒数、キーが存在しない場合-2、有効期限なしの場合-1
        """
        try:
            result = await self.client.ttl(key)
            return int(result)
        except RedisError as e:
            logger.error(f"TTL取得エラー: {key}, {e}")
            return -2


class RedisJSONCache(RedisCache):
    """JSON形式でのRedisキャッシュ操作を提供するクラス"""

    async def get_json(self, key: str) -> Any | None:
        """JSON形式で保存された値を取得

        Args:
            key: 取得するキー

        Returns:
            デシリアライズされたPythonオブジェクト
        """
        try:
            value = await self.get(key)
            if value is None:
                return None
            return json.loads(value)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"JSON デシリアライズエラー: {key}, {e}")
            return None

    async def set_json(self, key: str, value: Any, expire: int | None = None) -> bool:
        """PythonオブジェクトをJSON形式で保存

        Args:
            key: 設定するキー
            value: 設定するPythonオブジェクト
            expire: 有効期限（秒）

        Returns:
            設定に成功した場合True
        """
        try:
            json_value = json.dumps(value, ensure_ascii=False, default=str)
            return await self.set(key, json_value, expire)
        except (TypeError, ValueError) as e:
            logger.error(f"JSON シリアライズエラー: {key}, {e}")
            return False


class RedisRateLimiter:
    """Redisを使用したレート制限機能を提供するクラス（IPアドレスやユーザーIDベースの制限）"""

    def __init__(self, manager: RedisManager | None = None) -> None:
        self.cache = RedisCache(manager)

    async def is_allowed(self, key: str, limit: int, window: int = 60, identifier: str = "request") -> bool:
        """レート制限をチェック

        Args:
            key: 制限対象のキー（IP、ユーザーID等）
            limit: 制限数
            window: 時間窓（秒）
            identifier: 識別子

        Returns:
            制限内の場合True、制限超過の場合False
        """
        redis_key = f"rate_limit:{identifier}:{key}"

        try:
            # 現在のカウント取得
            current = await self.cache.get(redis_key)

            if current is None:
                # 初回アクセス
                await self.cache.set(redis_key, "1", expire=window)
                return True
            else:
                current_count = int(current)
                if current_count >= limit:
                    return False
                else:
                    # カウントアップ
                    await self.cache.client.incr(redis_key)
                    return True

        except (ValueError, RedisError) as e:
            logger.error(f"レート制限エラー: {redis_key}, {e}")
            # エラー時は制限を無効化
            return True

    async def get_remaining(self, key: str, limit: int, identifier: str = "request") -> dict[str, int]:
        """レート制限の残り情報を取得

        Args:
            key: 制限対象のキー
            limit: 制限数
            identifier: 識別子

        Returns:
            残り回数とリセット時間を含む辞書
        """
        redis_key = f"rate_limit:{identifier}:{key}"

        try:
            current = await self.cache.get(redis_key)
            ttl = await self.cache.ttl(redis_key)

            current_count = int(current) if current else 0
            remaining = max(0, limit - current_count)
            reset_time = ttl if ttl > 0 else 0

            return {
                "remaining": remaining,
                "reset_time": reset_time,
                "limit": limit,
                "current": current_count,
            }

        except (ValueError, RedisError) as e:
            logger.error(f"レート制限情報取得エラー: {redis_key}, {e}")
            return {
                "remaining": limit,
                "reset_time": 0,
                "limit": limit,
                "current": 0,
            }


# アプリケーションライフサイクル管理
async def init_redis() -> None:
    try:
        # シングルトンインスタンスを取得
        manager = get_redis_manager()

        # 設定検証を含む接続プールとクライアント初期化
        manager.create_connection_pool()  # 内部で_validate_redis_settings()実行
        manager.create_client()

        # 接続テスト
        is_connected = await manager.ping()
        if not is_connected:
            raise RuntimeError("Redisへの接続に失敗しました")

        logger.info("Redisの初期化が完了しました")

    except ValueError as e:
        logger.error(f"Redis設定エラー: {e}")
        raise
    except Exception as e:
        logger.error(f"Redis初期化中にエラーが発生しました: {e}")
        raise


async def close_redis() -> None:
    try:
        manager = get_redis_manager()
        await manager.close()
        logger.info("Redis接続を正常に閉じました")

    except Exception as e:
        logger.error(f"Redis接続の終了中にエラーが発生しました: {e}")


async def health_check() -> dict[str, Any]:
    try:
        manager = get_redis_manager()
        is_connected = await manager.ping()

        if is_connected:
            return {
                "status": "healthy",
                "redis": "connected",
                "host": settings.REDIS_HOST,
                "port": settings.REDIS_PORT,
                "database": settings.REDIS_DB,
            }
        else:
            return {
                "status": "unhealthy",
                "redis": "disconnected",
                "error": "Ping failed",
            }

    except Exception as e:
        logger.error(f"Redisヘルスチェック中にエラーが発生しました: {e}")
        return {
            "status": "unhealthy",
            "redis": "error",
            "error": str(e),
        }


# ユーティリティー系インスタンス
cache = RedisCache()
json_cache = RedisJSONCache()
rate_limiter = RedisRateLimiter()


# 使用例とテスト用ユーティリティ
async def test_redis_operations() -> None:
    """Redis操作のテスト関数（開発用）"""
    if not settings.is_development:
        raise RuntimeError("この関数は開発環境でのみ実行可能です")

    try:
        logger.info("Redis操作テストを開始します")

        # 接続テスト
        manager = get_redis_manager()
        is_connected = await manager.ping()
        assert is_connected, "Redis接続に失敗しました"

        # キャッシュテスト
        test_key = "test:cache"
        test_value = "Hello Redis!"

        # 設定・取得テスト
        await cache.set(test_key, test_value, expire=60)
        cached_value = await cache.get(test_key)
        assert cached_value == test_value, f"キャッシュ値が一致しません: {cached_value}"

        # JSONキャッシュテスト
        json_test_key = "test:json"
        json_test_value = {"name": "SimpleTask", "version": "1.0.0"}

        await json_cache.set_json(json_test_key, json_test_value, expire=60)
        cached_json = await json_cache.get_json(json_test_key)
        assert cached_json == json_test_value, f"JSONキャッシュ値が一致しません: {cached_json}"

        # レート制限テスト
        test_ip = "127.0.0.1"
        is_allowed1 = await rate_limiter.is_allowed(test_ip, limit=3, window=60)
        is_allowed2 = await rate_limiter.is_allowed(test_ip, limit=3, window=60)
        remaining_info = await rate_limiter.get_remaining(test_ip, limit=3)

        assert is_allowed1, "1回目のレート制限チェックが失敗しました"
        assert is_allowed2, "2回目のレート制限チェックが失敗しました"
        assert remaining_info["remaining"] <= 3, f"残り回数が不正です: {remaining_info}"

        # クリーンアップ
        await cache.delete(test_key)
        await cache.delete(json_test_key)

        logger.info("Redis操作テストが正常に完了しました")

    except Exception as e:
        logger.error(f"Redis操作テスト中にエラーが発生しました: {e}")
        raise


if __name__ == "__main__":
    import asyncio

    async def main() -> None:
        """開発用メイン関数"""
        logging.basicConfig(level=logging.INFO)

        try:
            await init_redis()

            health = await health_check()
            print(f"ヘルスチェック結果: {health}")

            await test_redis_operations()

        finally:
            await close_redis()

    asyncio.run(main())
