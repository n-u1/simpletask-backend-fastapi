#!/bin/bash

# 環境変数の必須チェックスクリプト

set -e

echo "🔍 必須環境変数をチェックしています..."

# 必須環境変数リスト
REQUIRED_VARS=(
    "DB_USER"
    "DB_PASSWORD"
    "DB_NAME"
    "REDIS_PASSWORD"
    "JWT_SECRET_KEY"
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

# 結果表示
if [ ${#MISSING_VARS[@]} -eq 0 ]; then
    echo "✅ すべての必須環境変数が設定されています"
else
    echo "❌ 以下の環境変数が未設定または要変更です:"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "💡 解決方法:"
    echo "  1. .envファイルを編集して適切な値を設定"
    echo "  2. ./scripts/generate-secrets.sh で安全な値を生成"
    exit 1
fi

echo "🎯 環境変数チェック完了"
