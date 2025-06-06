"""エラーハンドリング関連ユーティリティ

エラーハンドリング、ログ出力、例外処理を提供
"""

import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, TypeVar

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


def get_logger(name: str) -> logging.Logger:
    """統一フォーマットのロガー取得

    Args:
        name: ロガー名（通常は __name__ を渡す）

    Returns:
        設定済みのロガーインスタンス
    """
    return logging.getLogger(name)


def handle_db_operation(operation_name: str) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """データベース操作用デコレータ

    データベース操作でエラーが発生した場合の統一処理を提供
    - エラーログの出力
    - データベースセッションのロールバック
    - 例外の再発生

    Args:
        operation_name: 操作名（ログ出力用）

    Usage:
        @handle_db_operation("ユーザー作成")
        async def create_user(db: AsyncSession, ...):
            # データベース操作
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            logger = get_logger(func.__module__)
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # データベースセッションがある場合はロールバック
                db = kwargs.get("db")
                if db and isinstance(db, AsyncSession):
                    try:
                        await db.rollback()
                    except Exception as rollback_error:
                        logger.error(f"ロールバック中にエラー: {rollback_error}")

                logger.error(f"{operation_name}エラー: {e}")
                raise

        return wrapper

    return decorator


def handle_service_error(
    operation_name: str, not_found_message: str | None = None
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """サービス層エラーハンドリング用デコレータ

    サービス層での統一されたエラーハンドリングを提供
    - 戻り値がNoneの場合の not_found エラー処理
    - 予期しない例外のキャッチとログ出力
    - 適切な例外への変換

    Args:
        operation_name: 操作名（ログ出力用）
        not_found_message: 戻り値がNoneの場合のエラーメッセージ

    Usage:
        @handle_service_error("タスク取得", "タスクが見つかりません")
        async def get_task(self, ...):
            # サービスロジック
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            logger = get_logger(func.__module__)
            try:
                result: T = await func(*args, **kwargs)

                # 戻り値がNoneで not_found_message が指定されている場合
                if result is None and not_found_message:
                    raise ValueError(not_found_message)

                return result

            except (ValueError, PermissionError):
                # ビジネスロジック例外はそのまま再発生
                raise
            except Exception as e:
                logger.error(f"{operation_name}中に予期しないエラー: {e}")
                raise RuntimeError(f"{operation_name}中にエラーが発生しました") from e

        return wrapper

    return decorator


def handle_api_error(operation_name: str) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """API層エラーハンドリング用デコレータ

    API層での統一されたエラーハンドリングを提供
    - ビジネス例外からHTTP例外への変換
    - 予期しない例外のログ出力と500エラー変換

    Args:
        operation_name: 操作名（ログ出力用）

    Usage:
        @handle_api_error("タスク作成")
        async def create_task(...):
            # API処理
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            logger = get_logger(func.__module__)
            try:
                return await func(*args, **kwargs)

            except ValueError as e:
                # バリデーションエラー
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
            except PermissionError as e:
                # 権限エラー
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
            except HTTPException:
                # 既にHTTPExceptionの場合はそのまま再発生
                raise
            except Exception as e:
                logger.error(f"{operation_name}中に予期しないエラー: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"{operation_name}中にエラーが発生しました",
                ) from e

        return wrapper

    return decorator


def create_http_exception(
    status_code: int,
    message: str,
    headers: dict[str, str] | None = None,
) -> HTTPException:
    """統一されたHTTPException生成

    Args:
        status_code: HTTPステータスコード
        message: エラーメッセージ
        headers: レスポンスヘッダー

    Returns:
        HTTPExceptionインスタンス
    """
    return HTTPException(status_code=status_code, detail=message, headers=headers)


def log_error(logger: logging.Logger, operation: str, error: Exception, **context: Any) -> None:
    """統一されたエラーログ出力

    Args:
        logger: ロガーインスタンス
        operation: 操作名
        error: 発生した例外
        **context: 追加のコンテキスト情報
    """
    context_str = ", ".join(f"{k}={v}" for k, v in context.items()) if context else ""
    log_message = f"{operation}エラー: {error}"
    if context_str:
        log_message += f" (context: {context_str})"

    logger.error(log_message)


def safe_operation(
    operation_name: str, default_return: Any = None
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """安全な操作実行デコレータ

    例外が発生してもアプリケーションを停止させない安全な操作用
    主にログ記録やキャッシュ操作などの副次的な処理で使用

    Args:
        operation_name: 操作名
        default_return: 例外発生時のデフォルト戻り値

    Usage:
        @safe_operation("キャッシュ更新", default_return=False)
        async def update_cache(...):
            # キャッシュ更新処理
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = get_logger(func.__module__)
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"{operation_name}中にエラーが発生しましたが処理を続行します: {e}")
                return default_return

        return wrapper

    return decorator


class ErrorContext:
    """エラーコンテキスト管理

    エラー発生時の追加情報を管理
    """

    def __init__(self, operation: str, **context: Any):
        self.operation = operation
        self.context = context
        self.logger = get_logger(self.__class__.__module__)

    def log_error(self, error: Exception) -> None:
        """エラーログ出力"""
        log_error(self.logger, self.operation, error, **self.context)

    def create_value_error(self, message: str) -> ValueError:
        """ValueError作成とログ出力"""
        error = ValueError(message)
        self.log_error(error)
        return error

    def create_permission_error(self, message: str) -> PermissionError:
        """PermissionError作成とログ出力"""
        error = PermissionError(message)
        self.log_error(error)
        return error
