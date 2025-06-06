"""ユーティリティモジュール

共通的な処理を提供するユーティリティ関数・クラス群
"""

from app.utils.db_helpers import (
    DatabaseSessionMixin,
    QueryBuilder,
    add_active_filter,
    add_default_ordering,
    add_pagination,
    add_user_filter,
    build_query,
    create_base_query,
    create_count_query,
    create_query_with_tag_tasks,
    create_query_with_task_tags,
    create_user_resource_query,
    safe_uuid_convert,
)
from app.utils.error_handler import (
    ErrorContext,
    create_http_exception,
    get_logger,
    handle_api_error,
    handle_db_operation,
    handle_service_error,
    log_error,
    safe_operation,
)
from app.utils.jwt_helpers import (
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_PASSWORD_RESET,
    TOKEN_TYPE_REFRESH,
    JWTHelper,
    create_access_token_payload,
    create_jwt_helper,
    create_password_reset_token_payload,
    create_refresh_token_payload,
    create_token_payload,
    decode_jwt_token,
    encode_jwt_token,
    extract_jti_from_token,
    extract_user_id_from_token,
    validate_token_type,
)
from app.utils.pagination import (
    PaginationParams,
    PaginationResult,
    calculate_pagination,
    create_pagination_result,
    validate_page_params,
)
from app.utils.permission import (
    HasActiveStatus,
    HasUserOwnership,
    PermissionChecker,
    check_resource_active_status,
    check_resource_ownership,
    create_permission_checker,
    ensure_resource_access,
    validate_resource_exists,
)

__all__ = [
    # Database utilities
    "DatabaseSessionMixin",
    "QueryBuilder",
    "add_active_filter",
    "add_default_ordering",
    "add_pagination",
    "add_user_filter",
    "build_query",
    "create_base_query",
    "create_count_query",
    "create_query_with_tag_tasks",
    "create_query_with_task_tags",
    "create_user_resource_query",
    "safe_uuid_convert",
    # Error handling utilities
    "ErrorContext",
    "create_http_exception",
    "get_logger",
    "handle_api_error",
    "handle_db_operation",
    "handle_service_error",
    "log_error",
    "safe_operation",
    # JWT utilities
    "JWTHelper",
    "TOKEN_TYPE_ACCESS",
    "TOKEN_TYPE_PASSWORD_RESET",
    "TOKEN_TYPE_REFRESH",
    "create_access_token_payload",
    "create_jwt_helper",
    "create_password_reset_token_payload",
    "create_refresh_token_payload",
    "create_token_payload",
    "decode_jwt_token",
    "encode_jwt_token",
    "extract_jti_from_token",
    "extract_user_id_from_token",
    "validate_token_type",
    # Pagination utilities
    "PaginationParams",
    "PaginationResult",
    "calculate_pagination",
    "create_pagination_result",
    "validate_page_params",
    # Permission utilities
    "HasActiveStatus",
    "HasUserOwnership",
    "PermissionChecker",
    "check_resource_active_status",
    "check_resource_ownership",
    "create_permission_checker",
    "ensure_resource_access",
    "validate_resource_exists",
]
