"""アプリケーション定数管理

バリデーション値、制限値、エラーメッセージを一元管理
"""

import re
from enum import Enum

# =============================================================================
# 認証・ユーザー関連定数
# =============================================================================


class UserConstants:
    """ユーザー関連の定数"""

    # パスワード設定
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_MAX_LENGTH = 128

    # 表示名設定
    DISPLAY_NAME_MIN_LENGTH = 2
    DISPLAY_NAME_MAX_LENGTH = 20

    # メール設定
    EMAIL_MAX_LENGTH = 255

    # アバター設定
    AVATAR_URL_MAX_LENGTH = 500

    # パスワード強度チェック
    WEAK_PASSWORDS = [  # nosec B105 # noqa: S105
        "password",
        "12345678",
        "qwerty",
        "admin",
        "user",
        "test",
        "123456789",
        "password123",
        "admin123",
    ]

    # 表示名に使用可能な文字パターン
    DISPLAY_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9ぁ-んァ-ヶー一-龠\s\-_\.]+$")

    # 画像ファイル拡張子
    ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".webp"]


# =============================================================================
# タスク関連定数
# =============================================================================


class TaskConstants:
    """タスク関連の定数"""

    # タスクタイトル設定
    TITLE_MIN_LENGTH = 1
    TITLE_MAX_LENGTH = 20

    # タスク説明設定
    DESCRIPTION_MAX_LENGTH = 2000

    # 位置情報設定
    POSITION_MIN = 0
    POSITION_MAX = 99999

    # デフォルト値
    DEFAULT_POSITION = 0
    DEFAULT_STATUS = "todo"
    DEFAULT_PRIORITY = "medium"


class TaskStatus(str, Enum):
    """タスクステータス列挙型"""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    ARCHIVED = "archived"


class TaskPriority(str, Enum):
    """タスク優先度列挙型"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# =============================================================================
# タグ関連定数
# =============================================================================


class TagConstants:
    """タグ関連の定数"""

    # タグ名設定
    NAME_MIN_LENGTH = 1
    NAME_MAX_LENGTH = 20

    # タグ説明設定
    DESCRIPTION_MAX_LENGTH = 200

    # カラーコード設定
    COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")
    DEFAULT_COLOR = "#3B82F6"

    # 使用可能なプリセットカラー
    PRESET_COLORS = [
        "#3B82F6",  # Blue
        "#EF4444",  # Red
        "#10B981",  # Green
        "#F59E0B",  # Yellow
        "#8B5CF6",  # Purple
        "#EC4899",  # Pink
        "#6B7280",  # Gray
        "#F97316",  # Orange
        "#06B6D4",  # Cyan
        "#84CC16",  # Lime
    ]


# =============================================================================
# API関連定数
# =============================================================================


class APIConstants:
    """API関連の定数"""

    # ページネーション設定
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    MIN_PAGE_SIZE = 1

    # 検索・フィルタリング設定
    SEARCH_MIN_LENGTH = 1
    SEARCH_MAX_LENGTH = 100

    # ソート設定
    DEFAULT_SORT_FIELD = "created_at"
    DEFAULT_SORT_ORDER = "desc"

    ALLOWED_SORT_ORDERS = ["asc", "desc"]

    # タスク用ソート可能フィールド
    TASK_SORTABLE_FIELDS = ["created_at", "updated_at", "title", "status", "priority", "due_date", "position"]

    # タグ用ソート可能フィールド
    TAG_SORTABLE_FIELDS = ["created_at", "updated_at", "name"]


# =============================================================================
# セキュリティ関連定数
# =============================================================================


class SecurityConstants:
    """セキュリティ関連の定数"""

    # JWT設定
    MIN_JWT_SECRET_LENGTH = 32

    # パスワードハッシュ設定
    MIN_DB_PASSWORD_LENGTH_PRODUCTION = 12
    MIN_REDIS_PASSWORD_LENGTH_PRODUCTION = 12

    # Argon2設定範囲
    ARGON2_TIME_COST_MIN = 1
    ARGON2_TIME_COST_MAX = 10
    ARGON2_TIME_COST_PRODUCTION_MIN = 3

    ARGON2_MEMORY_COST_MIN = 1024  # 1KB
    ARGON2_MEMORY_COST_MAX = 1048576  # 1GB
    ARGON2_MEMORY_COST_PRODUCTION_MIN = 65536  # 64KB

    ARGON2_PARALLELISM_MIN = 1
    ARGON2_PARALLELISM_MAX = 16

    # レート制限設定
    DEFAULT_RATE_LIMIT_PER_MINUTE = 60
    DEFAULT_LOGIN_RATE_LIMIT_PER_MINUTE = 5

    # セッション設定
    DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
    DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS = 30


# =============================================================================
# データベース関連定数
# =============================================================================


class DatabaseConstants:
    """データベース関連の定数"""

    # 接続プール設定
    DB_POOL_SIZE_MIN = 1
    DB_POOL_SIZE_MAX = 50
    DB_MAX_OVERFLOW_MIN = 0
    DB_MAX_OVERFLOW_MAX = 100

    # Redis設定
    REDIS_PORT_MIN = 1
    REDIS_PORT_MAX = 65535
    REDIS_DB_MIN = 0
    REDIS_DB_MAX = 15
    REDIS_POOL_SIZE_MIN = 1
    REDIS_POOL_SIZE_MAX = 100


# =============================================================================
# レスポンスメッセージ定数
# =============================================================================


class SuccessMessages:
    """成功メッセージの定数"""

    # 認証関連
    USER_CREATED = "ユーザーが正常に作成されました"
    LOGIN_SUCCESS = "ログインしました"
    LOGOUT_SUCCESS = "ログアウトしました"
    PASSWORD_CHANGED = "パスワードが変更されました"  # nosec B105 # noqa: S105

    # タスク関連
    TASK_CREATED = "タスクが作成されました"
    TASK_UPDATED = "タスクが更新されました"
    TASK_DELETED = "タスクが削除されました"
    TASK_STATUS_UPDATED = "タスクのステータスが更新されました"

    # タグ関連
    TAG_CREATED = "タグが作成されました"
    TAG_UPDATED = "タグが更新されました"
    TAG_DELETED = "タグが削除されました"


# =============================================================================
# ヘルパー関数
# =============================================================================


def validate_color_code(color: str) -> bool:
    """カラーコードの妥当性をチェック

    Args:
        color: チェック対象のカラーコード

    Returns:
        有効な場合True、無効な場合False
    """
    return bool(TagConstants.COLOR_PATTERN.match(color))


def validate_display_name(name: str) -> bool:
    """表示名の妥当性をチェック

    Args:
        name: チェック対象の表示名

    Returns:
        有効な場合True、無効な場合False
    """
    if not name or len(name.strip()) < UserConstants.DISPLAY_NAME_MIN_LENGTH:
        return False

    if len(name.strip()) > UserConstants.DISPLAY_NAME_MAX_LENGTH:
        return False

    return bool(UserConstants.DISPLAY_NAME_PATTERN.match(name.strip()))


def is_weak_password(password: str) -> bool:  # nosec B105 # noqa: S105
    """弱いパスワードかどうかをチェック

    Args:
        password: チェック対象のパスワード

    Returns:
        弱いパスワードの場合True、そうでなければFalse
    """
    return password.lower() in UserConstants.WEAK_PASSWORDS


def validate_image_url(url: str) -> bool:
    """画像URLの妥当性をチェック

    Args:
        url: チェック対象のURL

    Returns:
        有効な画像URLの場合True、無効な場合False
    """
    if not url:
        return False

    # URL形式の基本チェック
    url_pattern = re.compile(r"^https?://[^\s/$.?#].[^\s]*$")
    if not url_pattern.match(url):
        return False

    # 画像拡張子チェック
    return any(url.lower().endswith(ext) for ext in UserConstants.ALLOWED_IMAGE_EXTENSIONS)


# =============================================================================
# エラーメッセージ定数
# =============================================================================


class ErrorMessages:
    """エラーメッセージの定数"""

    # 認証関連
    INVALID_CREDENTIALS = "メールアドレスまたはパスワードが正しくありません"
    USER_NOT_FOUND = "ユーザーが見つかりません"
    USER_INACTIVE = "アカウントが無効化されています"
    EMAIL_ALREADY_EXISTS = "このメールアドレスは既に登録されています"

    # パスワード関連
    PASSWORD_TOO_SHORT = f"パスワードは{UserConstants.PASSWORD_MIN_LENGTH}文字以上である必要があります"  # nosec B105 # noqa: S105
    PASSWORD_TOO_LONG = f"パスワードは{UserConstants.PASSWORD_MAX_LENGTH}文字以内で入力してください"  # nosec B105 # noqa: S105
    PASSWORD_NO_LETTERS = "パスワードには英字を含めてください"  # nosec B105 # noqa: S105
    PASSWORD_NO_NUMBERS = "パスワードには数字を含めてください"  # nosec B105 # noqa: S105
    PASSWORD_TOO_WEAK = "このパスワードは簡単すぎるため使用できません"  # nosec B105 # noqa: S105

    # 表示名関連
    DISPLAY_NAME_TOO_SHORT = f"表示名は{UserConstants.DISPLAY_NAME_MIN_LENGTH}文字以上で入力してください"
    DISPLAY_NAME_TOO_LONG = f"表示名は{UserConstants.DISPLAY_NAME_MAX_LENGTH}文字以内で入力してください"
    DISPLAY_NAME_INVALID_CHARS = "表示名に使用できない文字が含まれています"

    # タスク関連
    TASK_NOT_FOUND = "タスクが見つかりません"
    TASK_TITLE_REQUIRED = "タスクタイトルは必須です"
    TASK_TITLE_TOO_LONG = f"タスクタイトルは{TaskConstants.TITLE_MAX_LENGTH}文字以内で入力してください"
    TASK_ACCESS_DENIED = "このタスクにアクセスする権限がありません"

    # タグ関連
    TAG_NOT_FOUND = "タグが見つかりません"
    TAG_NAME_REQUIRED = "タグ名は必須です"
    TAG_NAME_TOO_LONG = f"タグ名は{TagConstants.NAME_MAX_LENGTH}文字以内で入力してください"
    TAG_NAME_DUPLICATE = "このタグ名は既に使用されています"
    TAG_COLOR_INVALID = "有効なカラーコード（#RRGGBB形式）を入力してください"
    TAG_ACCESS_DENIED = "このタグにアクセスする権限がありません"

    # API関連
    INVALID_PAGE_SIZE = (
        f"ページサイズは{APIConstants.MIN_PAGE_SIZE}以上{APIConstants.MAX_PAGE_SIZE}以下で指定してください"
    )
    INVALID_SORT_FIELD = "指定されたソートフィールドは無効です"
    INVALID_SORT_ORDER = "ソート順序は'asc'または'desc'を指定してください"

    # リソース関連（汎用）
    RESOURCE_NOT_FOUND = "指定されたリソースが見つかりません"
    RESOURCE_ACCESS_DENIED = "このリソースにアクセスする権限がありません"
    INACTIVE_RESOURCE = "このリソースは無効化されています"

    # ユーザープロフィール関連
    PROFILE_ACCESS_DENIED = "他のユーザーのプロフィールにアクセスする権限がありません"

    # 一般的なエラー
    VALIDATION_ERROR = "入力値に誤りがあります"
    SERVER_ERROR = "サーバーエラーが発生しました"
    NOT_FOUND = "リソースが見つかりません"
    UNAUTHORIZED = "認証が必要です"
    FORBIDDEN = "アクセスが拒否されました"
    RATE_LIMIT_EXCEEDED = "リクエスト制限を超過しました"


# =============================================================================
# 型定義用のエイリアス
# =============================================================================

# タスクステータスの型
TaskStatusType = TaskStatus

# タスク優先度の型
TaskPriorityType = TaskPriority
