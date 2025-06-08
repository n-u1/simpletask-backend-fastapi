#!/bin/bash

# 環境変数の必須チェックスクリプト

set -e

echo "🔍 必須環境変数をチェックしています..."

REQUIRED_VARS=(
    "DB_USER"
    "DB_PASSWORD"
    "DB_NAME"
    "DB_HOST"
    "REDIS_HOST"
    "REDIS_PASSWORD"
    "JWT_SECRET_KEY"
    "JWT_ALGORITHM"
)

RECOMMENDED_VARS=(
    "ENVIRONMENT"
    "LOG_LEVEL"
    "DEBUG"
    "DB_PORT"
    "REDIS_PORT"
    "BACKEND_CORS_ORIGINS"
    "JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    "JWT_REFRESH_TOKEN_EXPIRE_DAYS"
    "ARGON2_TIME_COST"
    "ARGON2_MEMORY_COST"
    "ARGON2_PARALLELISM"
    "ARGON2_HASH_LENGTH"
    "ARGON2_SALT_LENGTH"
    "DB_POOL_SIZE"
    "REDIS_POOL_SIZE"
    "REDIS_HEALTH_CHECK_INTERVAL"
)

MISSING_VARS=()

# .envファイルを読み込み
if [ -f .env ]; then
    source .env
else
    echo "❌ エラー: .envファイルが見つかりません"
    echo "cp .env.example .env を実行してください"
    exit 1
fi

# 各変数をチェック
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    elif [[ "${!var}" == "CHANGE_ME"* ]]; then
        echo "⚠️  警告: $var がデフォルト値のままです: ${!var}"
        MISSING_VARS+=("$var")
    fi
done

# 推奨変数のチェック
MISSING_RECOMMENDED=()
for var in "${RECOMMENDED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_RECOMMENDED+=("$var")
    elif [[ "${!var}" == "CHANGE_ME"* ]]; then
        MISSING_RECOMMENDED+=("$var")
    fi
done

# 結果表示
if [ ${#MISSING_VARS[@]} -eq 0 ]; then
    echo "✅ すべての必須環境変数が設定されています"
else
    echo "❌ 以下の必須環境変数が未設定または要変更です:"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "💡 解決方法:"
    echo "  1. .envファイルを編集して適切な値を設定"
    echo "  2. ./scripts/generate-secrets.sh で安全な値を生成"
    exit 1
fi

# 推奨変数の結果表示
if [ ${#MISSING_RECOMMENDED[@]} -gt 0 ]; then
    echo "⚠️  以下の推奨環境変数が未設定です:"
    for var in "${MISSING_RECOMMENDED[@]}"; do
        echo "  - $var"
    done
    echo "💡 これらの変数は必須ではありませんが、設定することを推奨します"
    echo ""
fi

# セキュリティチェック
echo "🔒 セキュリティ設定をチェック..."

# JWTアルゴリズムの妥当性チェック
if [[ "$JWT_ALGORITHM" != "HS256" && "$JWT_ALGORITHM" != "HS384" && "$JWT_ALGORITHM" != "HS512" ]]; then
    echo "⚠️  警告: JWT_ALGORITHM が推奨値ではありません ($JWT_ALGORITHM)"
    echo "💡 推奨: HS256, HS384, HS512"
fi

# 本番環境での設定チェック
if [[ "$ENVIRONMENT" == "production" ]]; then
    echo "🏭 本番環境設定をチェック..."

    if [[ "$DEBUG" == "True" || "$DEBUG" == "true" ]]; then
        echo "⚠️  警告: 本番環境でDEBUG=Trueは推奨されません"
    fi

    if [[ "$LOG_LEVEL" == "DEBUG" || "$LOG_LEVEL" == "debug" ]]; then
        echo "⚠️  警告: 本番環境でLOG_LEVEL=DEBUGは推奨されません"
    fi
fi

echo "🎯 環境変数チェック完了"
