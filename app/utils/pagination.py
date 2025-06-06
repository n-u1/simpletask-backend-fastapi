"""ページネーション関連ユーティリティ

ページネーション計算と制限値チェック処理を提供
"""

from typing import NamedTuple

from app.core.constants import APIConstants


class PaginationParams(NamedTuple):
    """ページネーション計算結果"""

    skip: int
    limit: int
    page: int


class PaginationResult(NamedTuple):
    """ページネーション情報"""

    page: int
    per_page: int
    total_pages: int
    total: int


def calculate_pagination(page: int, per_page: int) -> PaginationParams:
    """ページネーションパラメータを計算

    Args:
        page: ページ番号（1から開始）
        per_page: 1ページあたりの件数

    Returns:
        計算されたページネーションパラメータ
    """
    # 制限値チェック
    validated_per_page = min(per_page, APIConstants.MAX_PAGE_SIZE)
    validated_per_page = max(validated_per_page, APIConstants.MIN_PAGE_SIZE)

    # ページ番号の正規化
    validated_page = max(page, 1)

    # skip値計算
    skip = (validated_page - 1) * validated_per_page

    return PaginationParams(
        skip=skip,
        limit=validated_per_page,
        page=validated_page,
    )


def create_pagination_result(page: int, per_page: int, total: int) -> PaginationResult:
    """ページネーション結果を作成

    Args:
        page: 現在のページ番号
        per_page: 1ページあたりの件数
        total: 総件数

    Returns:
        ページネーション情報
    """
    # 総ページ数計算（0件の場合は1ページとする）
    total_pages = max((total + per_page - 1) // per_page, 1) if total > 0 else 1

    return PaginationResult(
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total=total,
    )


def validate_page_params(page: int, per_page: int) -> tuple[int, int]:
    """ページネーションパラメータのバリデーション

    Args:
        page: ページ番号
        per_page: 1ページあたりの件数

    Returns:
        バリデーション済みの (page, per_page) タプル

    Raises:
        ValueError: パラメータが無効な場合
    """
    if page < 1:
        raise ValueError("ページ番号は1以上である必要があります")

    if per_page < APIConstants.MIN_PAGE_SIZE:
        raise ValueError(f"1ページあたりの件数は{APIConstants.MIN_PAGE_SIZE}以上である必要があります")

    if per_page > APIConstants.MAX_PAGE_SIZE:
        raise ValueError(f"1ページあたりの件数は{APIConstants.MAX_PAGE_SIZE}以下である必要があります")

    return page, per_page
