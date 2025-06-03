"""FastAPIアプリケーションのメインモジュール

ミドルウェア、ルーティング、ライフサイクル管理を提供
"""

import logging
import time
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, cast

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.database import close_database, init_database
from app.core.database import health_check as db_health_check
from app.core.redis import close_redis, init_redis
from app.core.redis import health_check as redis_health_check

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL), format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """アプリケーションライフサイクル管理"""
    # 起動時処理
    logger.info("🚀 SimpleTask API を起動しています...")

    try:
        logger.info("📊 データベース接続を初期化中...")
        await init_database()

        logger.info("📡 Redis接続を初期化中...")
        await init_redis()

        logger.info("✅ すべてのサービスが正常に初期化されました")

    except Exception as e:
        logger.error(f"❌ 初期化中にエラーが発生しました: {e}")
        raise

    yield

    # 終了時処理
    logger.info("🛑 SimpleTask API を終了しています...")

    try:
        await close_database()

        await close_redis()

        logger.info("✅ すべてのサービスが正常に終了しました")

    except Exception as e:
        logger.error(f"❌ 終了処理中にエラーが発生しました: {e}")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """セキュリティヘッダーを追加するミドルウェア"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """リクエストを処理し、セキュリティヘッダーを追加"""
        response = await call_next(request)

        # セキュリティヘッダー設定
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Content-Security-Policy"] = "default-src 'self'"

        # 開発環境では処理時間を表示
        if settings.is_development and hasattr(request.state, "start_time"):
            process_time = time.time() - request.state.start_time
            response.headers["X-Process-Time"] = str(process_time)

        return cast("Response", response)


class ProcessTimeMiddleware(BaseHTTPMiddleware):
    """リクエスト処理時間を測定するミドルウェア（開発環境用）"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if settings.is_development:
            request.state.start_time = time.time()

        response = await call_next(request)
        return cast("Response", response)


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        description="タスク管理WebアプリケーションのAPI",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )

    setup_middleware(app)

    setup_routes(app)

    setup_exception_handlers(app)

    return app


def setup_middleware(app: FastAPI) -> None:
    app.add_middleware(SecurityHeadersMiddleware)

    if settings.is_development:
        app.add_middleware(ProcessTimeMiddleware)

    cors_config = settings.get_cors_config()
    app.add_middleware(CORSMiddleware, **cors_config)

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

    logger.info("ミドルウェアの設定が完了しました")


def setup_routes(app: FastAPI) -> None:
    @app.get("/health")
    async def health_check() -> dict[str, Any] | JSONResponse:
        try:
            db_health = await db_health_check()

            redis_health = await redis_health_check()

            overall_status = (
                "healthy"
                if (db_health.get("status") == "healthy" and redis_health.get("status") == "healthy")
                else "unhealthy"
            )

            return {
                "status": overall_status,
                "timestamp": datetime.now(UTC).isoformat(),
                "version": settings.PROJECT_VERSION,
                "environment": settings.ENVIRONMENT,
                "services": {"database": db_health, "redis": redis_health},
            }

        except Exception as e:
            logger.error(f"ヘルスチェック中にエラーが発生しました: {e}")
            return JSONResponse(
                status_code=503,
                content={
                    "error": "health_check_failed",
                    "message": "ヘルスチェックに失敗しました",
                    "details": str(e),
                    "path": "/health",
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            )

    @app.get("/")
    async def root() -> dict[str, Any]:
        return {
            "message": f"Welcome to {settings.PROJECT_NAME}",
            "version": settings.PROJECT_VERSION,
            "environment": settings.ENVIRONMENT,
            "docs_url": "/docs" if settings.is_development else None,
            "health_url": "/health",
        }

    # TODO: APIルーターを追加
    # app.include_router(
    #     auth_router,
    #     prefix=f"{settings.API_V1_STR}/auth",
    #     tags=["認証"]
    # )
    # app.include_router(
    #     users_router,
    #     prefix=f"{settings.API_V1_STR}/users",
    #     tags=["ユーザー"]
    # )
    # app.include_router(
    #     tasks_router,
    #     prefix=f"{settings.API_V1_STR}/tasks",
    #     tags=["タスク"]
    # )
    # app.include_router(
    #     tags_router,
    #     prefix=f"{settings.API_V1_STR}/tags",
    #     tags=["タグ"]
    # )

    logger.info("ルーティングの設定が完了しました")


def setup_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "http_error",
                "message": exc.detail,
                "status_code": exc.status_code,
                "path": str(request.url.path),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": "リクエストの形式が正しくありません",
                "details": [
                    {
                        "field": ".".join(str(loc) for loc in error["loc"]),
                        "message": error["msg"],
                        "type": error["type"],
                    }
                    for error in exc.errors()
                ],
                "path": str(request.url.path),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(f"予期しない例外が発生しました: {exc}", exc_info=True)

        # 本番環境では詳細なエラー情報を隠す
        error_detail = "内部サーバーエラーが発生しました" if settings.is_production else str(exc)

        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": error_detail,
                "path": str(request.url.path),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    logger.info("例外ハンドラーの設定が完了しました")


# アプリケーションのインスタンスを作成
app = create_application()


# 開発用の追加機能
if settings.is_development:

    @app.get("/debug/config")
    async def debug_config() -> dict[str, Any]:
        """開発環境用設定情報エンドポイント"""
        return {
            "project_name": settings.PROJECT_NAME,
            "version": settings.PROJECT_VERSION,
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "log_level": settings.LOG_LEVEL,
            "database": {
                "host": settings.DB_HOST,
                "port": settings.DB_PORT,
                "name": settings.DB_NAME,
                "user": settings.DB_USER,
                # パスワードは除外
            },
            "redis": {
                "host": settings.REDIS_HOST,
                "port": settings.REDIS_PORT,
                "db": settings.REDIS_DB,
                # パスワードは除外
            },
            "cors_origins": settings.BACKEND_CORS_ORIGINS,
            "allowed_hosts": settings.ALLOWED_HOSTS,
        }

    logger.info("開発環境用エンドポイントが有効になりました")


if __name__ == "__main__":
    import uvicorn

    # 開発サーバー起動
    if settings.is_development:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",  # nosec B104 # noqa: S104 # 開発環境のみ全インターフェースにバインド
            port=8000,
            reload=True,
            log_level=settings.LOG_LEVEL.lower(),
            access_log=True,
        )
    else:
        logger.warning("本番環境では uvicorn main:app で起動してください")
