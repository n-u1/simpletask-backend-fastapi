"""API v1 ルーター統合

すべてのv1 APIエンドポイントを統合
"""

from typing import Any

from fastapi import APIRouter

from app.api.v1 import auth, tags, tasks, users

# メインのAPIルーター
api_router = APIRouter()

# 認証関連エンドポイント
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["認証"],
    responses={
        401: {"description": "認証が必要です"},
        403: {"description": "アクセスが拒否されました"},
        422: {"description": "入力値に誤りがあります"},
        429: {"description": "リクエスト制限を超過しました"},
    },
)

# ユーザー管理エンドポイント
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["ユーザー管理"],
    dependencies=[],  # 認証は各エンドポイントで個別に設定
    responses={
        401: {"description": "認証が必要です"},
        403: {"description": "アクセスが拒否されました"},
        404: {"description": "ユーザーが見つかりません"},
    },
)

# タスク管理エンドポイント
api_router.include_router(
    tasks.router,
    prefix="/tasks",
    tags=["タスク管理"],
    dependencies=[],  # 認証は各エンドポイントで個別に設定
    responses={
        400: {"description": "リクエストが不正です"},
        401: {"description": "認証が必要です"},
        403: {"description": "このタスクにアクセスする権限がありません"},
        404: {"description": "タスクが見つかりません"},
    },
)

# タグ管理エンドポイント
api_router.include_router(
    tags.router,
    prefix="/tags",
    tags=["タグ管理"],
    dependencies=[],  # 認証は各エンドポイントで個別に設定
    responses={
        400: {"description": "リクエストが不正です"},
        401: {"description": "認証が必要です"},
        403: {"description": "このタグにアクセスする権限がありません"},
        404: {"description": "タグが見つかりません"},
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
