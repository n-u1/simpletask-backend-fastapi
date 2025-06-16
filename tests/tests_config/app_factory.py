"""テスト用FastAPIアプリケーション作成"""

import logging
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from tests.tests_config.schema_overrides import setup_schema_overrides


def create_test_app() -> FastAPI:
    """テスト環境用のFastAPIアプリケーションを作成"""
    # ログ設定
    logger = logging.getLogger(__name__)

    # スキーマ置き換えを実行
    setup_schema_overrides()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        description="SimpleTask API - テスト環境",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
    )

    # ミドルウェア設定
    _setup_middleware(app, logger)

    # ルーター設定
    _setup_routes(app)

    return app


def _setup_middleware(app: FastAPI, logger: logging.Logger) -> None:
    """ミドルウェアを設定"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next: Any) -> Any:
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"{request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s")
        return response

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content={"error": "http_error", "message": exc.detail, "details": None}
        )


def _setup_routes(app: FastAPI) -> None:
    """ルートを設定"""
    from app.api.v1.router import api_router

    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.get("/health")
    async def health_check() -> dict[str, Any]:
        return {"status": "healthy", "environment": "testing", "version": settings.PROJECT_VERSION}
