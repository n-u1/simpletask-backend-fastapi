"""API v1 ルーター統合

すべてのv1 APIエンドポイントを統合
"""

from typing import Any

from fastapi import APIRouter

from app.api.v1 import auth, tags, tasks, users
from app.core.constants import ErrorMessages

# メインのAPIルーター
api_router = APIRouter()

# 認証関連エンドポイント
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["認証"],
    responses={
        401: {"description": ErrorMessages.UNAUTHORIZED},
        403: {"description": ErrorMessages.FORBIDDEN},
        422: {"description": ErrorMessages.VALIDATION_ERROR},
        429: {"description": ErrorMessages.RATE_LIMIT_EXCEEDED},
    },
)

# ユーザー管理エンドポイント
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["ユーザー管理"],
    dependencies=[],  # 認証は各エンドポイントで個別に設定
    responses={
        401: {"description": ErrorMessages.UNAUTHORIZED},
        403: {"description": ErrorMessages.FORBIDDEN},
        404: {"description": ErrorMessages.USER_NOT_FOUND},
    },
)

# タスク管理エンドポイント
api_router.include_router(
    tasks.router,
    prefix="/tasks",
    tags=["タスク管理"],
    dependencies=[],  # 認証は各エンドポイントで個別に設定
    responses={
        400: {"description": ErrorMessages.BAD_REQUEST},
        401: {"description": ErrorMessages.UNAUTHORIZED},
        403: {"description": ErrorMessages.TASK_ACCESS_DENIED},
        404: {"description": ErrorMessages.TASK_NOT_FOUND},
    },
)

# タグ管理エンドポイント
api_router.include_router(
    tags.router,
    prefix="/tags",
    tags=["タグ管理"],
    dependencies=[],  # 認証は各エンドポイントで個別に設定
    responses={
        400: {"description": ErrorMessages.BAD_REQUEST},
        401: {"description": ErrorMessages.UNAUTHORIZED},
        403: {"description": ErrorMessages.TAG_ACCESS_DENIED},
        404: {"description": ErrorMessages.TAG_NOT_FOUND},
    },
)


# ルーター情報（デバッグ用）
@api_router.get("/", include_in_schema=False)
async def api_info() -> dict[str, Any]:
    """API情報を取得（デバッグ用）"""
    return {
        "message": "SimpleTask API v1",
        "version": "0.1.0",
        "endpoints": {"auth": "/auth/*", "users": "/users/*", "tasks": "/tasks/*", "tags": "/tags/*"},
        "documentation": {"swagger": "/docs", "redoc": "/redoc", "openapi": "/openapi.json"},
    }


__all__ = ["api_router"]
