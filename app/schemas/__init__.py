"""スキーマパッケージ

Pydanticスキーマを提供
"""

# Auth関連スキーマ
from app.schemas.auth import (
    AuthResponse,
    AuthUserResponse,
    PasswordChangeRequest,
    RefreshTokenRequest,
    Token,
    TokenPayload,
    UserCreate,
    UserLogin,
)

# Tag関連スキーマ
from app.schemas.tag import (
    TagCreate,
    TagFilters,
    TagListResponse,
    TagResponse,
    TagSortOptions,
    TagSummary,
    TagUpdate,
)

# Task関連スキーマ
from app.schemas.task import (
    TagInfo,
    TaskCreate,
    TaskFilters,
    TaskListResponse,
    TaskPositionUpdate,
    TaskResponse,
    TaskSortOptions,
    TaskStatusUpdate,
    TaskUpdate,
)

# User関連スキーマ
from app.schemas.user import (
    UserProfileUpdate,
    UserResponse,
    UserSummary,
    UserUpdate,
)

__all__ = [
    # Tag関連
    "TagCreate",
    "TagUpdate",
    "TagResponse",
    "TagSummary",
    "TagListResponse",
    "TagFilters",
    "TagSortOptions",
    # Task関連
    "TaskCreate",
    "TaskUpdate",
    "TaskResponse",
    "TaskListResponse",
    "TaskStatusUpdate",
    "TaskPositionUpdate",
    "TaskFilters",
    "TaskSortOptions",
    "TagInfo",
    # User関連
    "UserUpdate",
    "UserResponse",
    "UserSummary",
    "UserProfileUpdate",
    # Auth関連
    "UserCreate",
    "UserLogin",
    "AuthUserResponse",
    "Token",
    "TokenPayload",
    "RefreshTokenRequest",
    "PasswordChangeRequest",
    "AuthResponse",
]
