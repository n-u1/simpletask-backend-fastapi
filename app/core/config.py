"""アプリケーション設定管理モジュール

Pydantic V2 BaseSettingsを使用した設定システムを提供
"""

import os
import secrets
from typing import TYPE_CHECKING, Any
from urllib.parse import quote_plus

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import DatabaseConstants, SecurityConstants


class Settings(BaseSettings):
    """アプリケーション設定

    Pydantic V2を使用して環境変数から設定を読み込む（設定は自動的に検証・型チェックされる）
    """

    # =============================================================================
    # Pydantic V2 設定
    # =============================================================================
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        validate_assignment=True,
    )

    # =============================================================================
    # アプリケーション設定
    # =============================================================================
    PROJECT_NAME: str = "SimpleTask API"
    PROJECT_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    API_V1_STR: str = "/api/v1"

    # =============================================================================
    # データベース設定
    # =============================================================================
    DB_USER: str = Field(...)
    DB_PASSWORD: str = Field(...)
    DB_NAME: str = Field(...)
    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=5432)
    DB_POOL_SIZE: int = Field(default=5)
    DB_MAX_OVERFLOW: int = Field(default=10)

    # =============================================================================
    # Redis設定
    # =============================================================================
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_PASSWORD: str = Field(...)
    REDIS_DB: int = Field(default=0)
    REDIS_POOL_SIZE: int = Field(default=5)
    REDIS_HEALTH_CHECK_INTERVAL: int = Field(default=30)
    REDIS_SOCKET_TIMEOUT_DEV: int = Field(default=5)
    REDIS_SOCKET_TIMEOUT_PROD: int = Field(default=10)

    # =============================================================================
    # JWT設定
    # =============================================================================
    JWT_SECRET_KEY: str = Field(...)
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30)

    # =============================================================================
    # Argon2パスワードハッシュ設定
    # =============================================================================
    ARGON2_TIME_COST: int = Field(default=3)
    ARGON2_MEMORY_COST: int = Field(default=65536)
    ARGON2_PARALLELISM: int = Field(default=1)
    ARGON2_HASH_LENGTH: int = Field(default=32)
    ARGON2_SALT_LENGTH: int = Field(default=16)

    # =============================================================================
    # CORS設定
    # =============================================================================
    BACKEND_CORS_ORIGINS: list[str] = []
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1"]

    # =============================================================================
    # レート制限
    # =============================================================================
    RATE_LIMIT_PER_MINUTE: int = Field(default=SecurityConstants.DEFAULT_RATE_LIMIT_PER_MINUTE)
    LOGIN_RATE_LIMIT_PER_MINUTE: int = Field(default=SecurityConstants.DEFAULT_LOGIN_RATE_LIMIT_PER_MINUTE)

    # =============================================================================
    # ログレベル設定
    # =============================================================================
    VALID_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    # =============================================================================
    # バリデーター（Pydantic V2）
    # =============================================================================

    @field_validator("JWT_SECRET_KEY", mode="before")
    @classmethod
    def validate_jwt_secret_key(cls, v: str) -> str:
        if not v or len(v) < SecurityConstants.MIN_JWT_SECRET_LENGTH:
            # 本番環境チェック
            env = os.getenv("ENVIRONMENT", "development").lower()
            if env == "production":
                raise ValueError(
                    f"JWT_SECRET_KEY must be at least {SecurityConstants.MIN_JWT_SECRET_LENGTH} "
                    "characters in production. Generate one using: "
                    'python -c "import secrets; print(secrets.token_urlsafe(32))"'
                )
            # 開発環境ではキーを自動生成
            return secrets.token_urlsafe(SecurityConstants.MIN_JWT_SECRET_LENGTH)
        return v

    @field_validator("JWT_ALGORITHM")
    @classmethod
    def validate_jwt_algorithm(cls, v: str) -> str:
        allowed_algorithms = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
        if v not in allowed_algorithms:
            raise ValueError(f"JWT_ALGORITHM must be one of: {', '.join(allowed_algorithms)}")
        return v

    @field_validator("ARGON2_TIME_COST")
    @classmethod
    def validate_argon2_time_cost(cls, v: int) -> int:
        if not (SecurityConstants.ARGON2_TIME_COST_MIN <= v <= SecurityConstants.ARGON2_TIME_COST_MAX):
            raise ValueError(
                f"ARGON2_TIME_COST must be between "
                f"{SecurityConstants.ARGON2_TIME_COST_MIN} and {SecurityConstants.ARGON2_TIME_COST_MAX}"
            )
        return v

    @field_validator("ARGON2_MEMORY_COST")
    @classmethod
    def validate_argon2_memory_cost(cls, v: int) -> int:
        if not (SecurityConstants.ARGON2_MEMORY_COST_MIN <= v <= SecurityConstants.ARGON2_MEMORY_COST_MAX):
            raise ValueError(
                f"ARGON2_MEMORY_COST must be between "
                f"{SecurityConstants.ARGON2_MEMORY_COST_MIN} and {SecurityConstants.ARGON2_MEMORY_COST_MAX}"
            )
        return v

    @field_validator("ARGON2_PARALLELISM")
    @classmethod
    def validate_argon2_parallelism(cls, v: int) -> int:
        if not (SecurityConstants.ARGON2_PARALLELISM_MIN <= v <= SecurityConstants.ARGON2_PARALLELISM_MAX):
            raise ValueError(
                f"ARGON2_PARALLELISM must be between "
                f"{SecurityConstants.ARGON2_PARALLELISM_MIN} and {SecurityConstants.ARGON2_PARALLELISM_MAX}"
            )
        return v

    @field_validator("DB_POOL_SIZE")
    @classmethod
    def validate_db_pool_size(cls, v: int) -> int:
        if not (DatabaseConstants.DB_POOL_SIZE_MIN <= v <= DatabaseConstants.DB_POOL_SIZE_MAX):
            raise ValueError(
                f"DB_POOL_SIZE must be between "
                f"{DatabaseConstants.DB_POOL_SIZE_MIN} and {DatabaseConstants.DB_POOL_SIZE_MAX}"
            )
        return v

    @field_validator("DB_MAX_OVERFLOW")
    @classmethod
    def validate_db_max_overflow(cls, v: int) -> int:
        if not (DatabaseConstants.DB_MAX_OVERFLOW_MIN <= v <= DatabaseConstants.DB_MAX_OVERFLOW_MAX):
            raise ValueError(
                f"DB_MAX_OVERFLOW must be between "
                f"{DatabaseConstants.DB_MAX_OVERFLOW_MIN} and {DatabaseConstants.DB_MAX_OVERFLOW_MAX}"
            )
        return v

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str] | None) -> list[str]:
        """CORS originをカンマ区切り文字列またはリストから解析"""
        if isinstance(v, str) and v:
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, list):
            return v
        return []

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def assemble_allowed_hosts(cls, v: str | list[str] | None) -> list[str]:
        """許可ホストをカンマ区切り文字列またはリストから解析(未提供の場合はlocalhostをデフォルトとして使用)"""
        if isinstance(v, str) and v:
            return [host.strip() for host in v.split(",") if host.strip()]
        elif isinstance(v, list):
            return v
        return cls.ALLOWED_HOSTS

    @field_validator("DB_PASSWORD", mode="before")
    @classmethod
    def validate_db_password(cls, v: str) -> str:
        if not v:
            raise ValueError("Database password is required")

        # 本番環境チェック
        env = os.getenv("ENVIRONMENT", "development").lower()
        if env == "production" and len(v) < SecurityConstants.MIN_DB_PASSWORD_LENGTH_PRODUCTION:
            raise ValueError(
                f"Database password must be at least "
                f"{SecurityConstants.MIN_DB_PASSWORD_LENGTH_PRODUCTION} characters in production"
            )

        return v

    @field_validator("REDIS_PASSWORD", mode="before")
    @classmethod
    def validate_redis_password(cls, v: str) -> str:
        if not v:
            raise ValueError("Redis password is required")

        # 本番環境チェック
        env = os.getenv("ENVIRONMENT", "development").lower()
        if env == "production" and len(v) < SecurityConstants.MIN_REDIS_PASSWORD_LENGTH_PRODUCTION:
            raise ValueError(
                f"Redis password must be at least "
                f"{SecurityConstants.MIN_REDIS_PASSWORD_LENGTH_PRODUCTION} characters in production"
            )

        return v

    @field_validator("LOG_LEVEL", mode="before")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        if v.upper() not in cls.VALID_LOG_LEVELS:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(cls.VALID_LOG_LEVELS)}")
        return v.upper()

    # =============================================================================
    # 計算プロパティ（Pydantic V2）
    # =============================================================================

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url_sync(self) -> str:
        """psycopg2用の同期PostgreSQL接続URLを生成"""
        encoded_password = quote_plus(self.DB_PASSWORD)
        return f"postgresql+psycopg2://{self.DB_USER}:{encoded_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url_async(self) -> str:
        """asyncpg用の非同期PostgreSQL接続URLを生成"""
        encoded_password = quote_plus(self.DB_PASSWORD)
        return f"postgresql+asyncpg://{self.DB_USER}:{encoded_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> str:
        """認証付きRedis接続URLを生成"""
        encoded_password = quote_plus(self.REDIS_PASSWORD)
        return f"redis://:{encoded_password}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_development(self) -> bool:
        """開発環境で実行中かチェック"""
        return self.ENVIRONMENT.lower() == "development"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        """本番環境で実行中かチェック"""
        return self.ENVIRONMENT.lower() == "production"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_testing(self) -> bool:
        """テスト環境で実行中かチェック"""
        return self.ENVIRONMENT.lower() == "testing"

    # =============================================================================
    # ヘルパーメソッド
    # =============================================================================

    def get_database_config(self) -> dict[str, Any]:
        return {
            "user": self.DB_USER,
            "password": self.DB_PASSWORD,
            "host": self.DB_HOST,
            "port": self.DB_PORT,
            "database": self.DB_NAME,
            "pool_size": self.DB_POOL_SIZE,
            "max_overflow": self.DB_MAX_OVERFLOW,
        }

    def get_redis_config(self) -> dict[str, Any]:
        return {
            "host": self.REDIS_HOST,
            "port": self.REDIS_PORT,
            "password": self.REDIS_PASSWORD,
            "db": self.REDIS_DB,
            "pool_size": self.REDIS_POOL_SIZE,
        }

    def get_argon2_config(self) -> dict[str, int]:
        """環境変数から読み込んだArgon2設定を返す"""
        return {
            "time_cost": self.ARGON2_TIME_COST,
            "memory_cost": self.ARGON2_MEMORY_COST,
            "parallelism": self.ARGON2_PARALLELISM,
            "hash_len": self.ARGON2_HASH_LENGTH,
            "salt_len": self.ARGON2_SALT_LENGTH,
        }

    def get_jwt_config(self) -> dict[str, Any]:
        """環境変数から読み込んだJWT設定を返す"""
        return {
            "secret_key": self.JWT_SECRET_KEY,
            "algorithm": self.JWT_ALGORITHM,
            "access_token_expire_minutes": self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
            "refresh_token_expire_days": self.JWT_REFRESH_TOKEN_EXPIRE_DAYS,
        }

    def get_cors_config(self) -> dict[str, Any]:
        return {
            "allow_origins": self.BACKEND_CORS_ORIGINS,
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": ["*"],
        }

    # =============================================================================
    # セキュリティ・検証メソッド
    # =============================================================================

    def validate_production_security(self) -> None:
        """本番環境のセキュリティ設定を検証"""
        if not self.is_production:
            return

        issues = []

        if len(self.JWT_SECRET_KEY) < SecurityConstants.MIN_JWT_SECRET_LENGTH:
            issues.append(f"JWT_SECRET_KEY must be at least {SecurityConstants.MIN_JWT_SECRET_LENGTH} characters")

        if len(self.DB_PASSWORD) < SecurityConstants.MIN_DB_PASSWORD_LENGTH_PRODUCTION:
            issues.append(
                f"DB_PASSWORD must be at least {SecurityConstants.MIN_DB_PASSWORD_LENGTH_PRODUCTION} characters"
            )

        if len(self.REDIS_PASSWORD) < SecurityConstants.MIN_REDIS_PASSWORD_LENGTH_PRODUCTION:
            issues.append(
                f"REDIS_PASSWORD must be at least {SecurityConstants.MIN_REDIS_PASSWORD_LENGTH_PRODUCTION} characters"
            )

        if not self.BACKEND_CORS_ORIGINS or "http://localhost" in str(self.BACKEND_CORS_ORIGINS):
            issues.append("CORS origins should not include localhost in production")

        if self.DEBUG:
            issues.append("DEBUG should be False in production")

        # Argon2パラメータの本番環境推奨値チェック
        if self.ARGON2_TIME_COST < SecurityConstants.ARGON2_TIME_COST_PRODUCTION_MIN:
            issues.append(
                f"ARGON2_TIME_COST should be at least {SecurityConstants.ARGON2_TIME_COST_PRODUCTION_MIN} in production"
            )

        if self.ARGON2_MEMORY_COST < SecurityConstants.ARGON2_MEMORY_COST_PRODUCTION_MIN:
            issues.append(
                f"ARGON2_MEMORY_COST should be at least {SecurityConstants.ARGON2_MEMORY_COST_PRODUCTION_MIN} "
                "in production"
            )

        if issues:
            raise ValueError(f"Production security issues: {'; '.join(issues)}")


# =============================================================================
# グローバル設定インスタンス（シングルトン）
# =============================================================================

_settings_instance: Settings | None = None


def get_settings() -> Settings:
    """シングルトンパターンで設定インスタンスを取得"""
    global _settings_instance

    if _settings_instance is None:
        # 環境変数からの設定読み込み
        if TYPE_CHECKING:
            # 型チェック時のみダミー値を使用(Lintの警告を回避)
            _settings_instance = Settings(
                DB_USER="dummy",
                DB_PASSWORD="dummy",  # nosec B106  # noqa: S106
                DB_NAME="dummy",
                REDIS_PASSWORD="dummy",  # nosec B106  # noqa: S106
                JWT_SECRET_KEY="dummy",  # nosec B106  # noqa: S106
            )
        else:
            # 実行時は環境変数から読み込み
            _settings_instance = Settings()

        # 本番環境セキュリティ検証（実行時のみ）
        if not TYPE_CHECKING:
            try:
                _settings_instance.validate_production_security()
            except ValueError as e:
                if _settings_instance.is_production:
                    raise
                else:
                    print(f"⚠️  開発モードセキュリティ通知: {e}")

    return _settings_instance


# グローバル設定インスタンス（アプリケーション全体で共有）
# MyPy対応：型チェック時は環境変数が不明なため、実行時に初期化
settings = get_settings()


# =============================================================================
# 開発ユーティリティ
# =============================================================================


def print_settings_summary() -> None:
    """現在の設定サマリーを表示"""
    print("=" * 60)
    print(f"🚀 {settings.PROJECT_NAME} v{settings.PROJECT_VERSION}")
    print("=" * 60)
    print(f"🏗️  Environment: {settings.ENVIRONMENT}")
    print(f"🐛 Debug Mode: {settings.DEBUG}")
    print(f"📊 Log Level: {settings.LOG_LEVEL}")
    print(f"🌐 API Prefix: {settings.API_V1_STR}")
    print("-" * 60)
    print("🗄️  Database Configuration:")
    print(f"   Host: {settings.DB_HOST}:{settings.DB_PORT}")
    print(f"   Database: {settings.DB_NAME}")
    print(f"   User: {settings.DB_USER}")
    print(f"   Pool Size: {settings.DB_POOL_SIZE}")
    print("-" * 60)
    print("📡 Redis Configuration:")
    print(f"   Host: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    print(f"   Database: {settings.REDIS_DB}")
    print(f"   Pool Size: {settings.REDIS_POOL_SIZE}")
    print("-" * 60)
    print("🔐 Security Configuration:")
    print(f"   JWT Algorithm: {settings.JWT_ALGORITHM}")
    print(f"   Access Token Expires: {settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES}min")
    print(f"   Refresh Token Expires: {settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS}days")
    print(f"   Argon2 Time Cost: {settings.ARGON2_TIME_COST}")
    print(f"   Argon2 Memory Cost: {settings.ARGON2_MEMORY_COST}")
    print(f"   Argon2 Parallelism: {settings.ARGON2_PARALLELISM}")
    print("-" * 60)
    print("🌐 Network Configuration:")
    cors_origins = ", ".join(settings.BACKEND_CORS_ORIGINS) if settings.BACKEND_CORS_ORIGINS else "None"
    print(f"   CORS Origins: {cors_origins}")
    allowed_hosts = ", ".join(settings.ALLOWED_HOSTS)
    print(f"   Allowed Hosts: {allowed_hosts}")
    print("-" * 60)
    print("🚦 Rate Limiting:")
    print(f"   General: {settings.RATE_LIMIT_PER_MINUTE}/min")
    print(f"   Login: {settings.LOGIN_RATE_LIMIT_PER_MINUTE}/min")
    print("=" * 60)


class SettingsValidationError(Exception):
    """設定検証エラー用のカスタム例外"""

    pass


# =============================================================================
# テスト用ユーティリティ
# =============================================================================


def reset_settings() -> None:
    """シングルトンインスタンスをリセット（主にテスト用）"""
    global _settings_instance
    _settings_instance = None


def create_test_settings(**overrides: Any) -> Settings:
    """テスト用設定でシングルトンを一時的に置き換えます

    この関数は安全な環境変数管理を行い、例外発生時も確実に復元します

    注意: この関数はテスト環境でのみ使用してください

    Args:
        **overrides: テスト用に上書きする設定

    Returns:
        テスト値を持つSettingsインスタンス

    Example:
        test_settings = create_test_settings(DB_NAME="test_db")
        try:
            # テスト実行
            pass
        finally:
            reset_settings()  # 必ずリセット
    """
    global _settings_instance

    # テストのデフォルト値
    test_defaults = {
        "ENVIRONMENT": "testing",
        "DEBUG": True,
        "DB_NAME": "simpletask_test",
        "REDIS_DB": 1,  # テスト用に異なるRedis DBを使用
        "JWT_SECRET_KEY": "test-secret-key-at-least-32-characters-long",
        "LOG_LEVEL": "WARNING",
    }

    # 提供された上書き設定をマージ
    test_defaults.update(overrides)

    # 元の環境変数を保存し、テスト用の値を設定
    original_env = {}
    for key, value in test_defaults.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = str(value)

    try:
        # 既存のシングルトンをリセットして新しいテスト設定で初期化
        _settings_instance = None
        test_settings = get_settings()
        return test_settings
    except Exception:
        # 例外が発生した場合は環境変数を復元
        for key, original_value in original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value

        _settings_instance = None
        raise
    # 注意: 正常終了時は環境変数を変更したまま
    # 呼び出し側でreset_settings()を呼ぶことで環境をクリーンアップ


if __name__ == "__main__":
    # 開発用テスト
    print_settings_summary()

    # 設定検証テスト
    try:
        if settings.is_production:
            settings.validate_production_security()
            print("✅ Production security validation passed")
        else:
            print("ℹ️  Development mode - security validation skipped")
    except ValueError as e:
        print(f"❌ Security validation failed: {e}")
