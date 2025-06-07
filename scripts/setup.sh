#!/bin/bash

# SimpleTask Backend セットアップスクリプト

set -e

echo "🚀 SimpleTask Backend セットアップを開始します..."

# 関数定義
check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "❌ エラー: $1 がインストールされていません"
        echo "💡 インストール方法:"
        case "$1" in
            "docker")
                echo "   https://docs.docker.com/get-docker/"
                ;;
            "docker-compose")
                echo "   https://docs.docker.com/compose/install/"
                ;;
            "git")
                echo "   sudo apt-get install git (Ubuntu/Debian)"
                echo "   brew install git (macOS)"
                ;;
        esac
        exit 1
    fi
}

# 必要なコマンドの存在確認
echo "🔍 必要なツールの確認..."
check_command "python3"
check_command "docker"
check_command "docker-compose"
check_command "git"

# Python バージョンチェック
# 3.13.x (任意のパッチバージョン) を許可、3.14以降は不許可
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
REQUIRED_VERSION="3.13"

if [[ ! "$PYTHON_VERSION" =~ ^3\.13\. ]]; then
    echo "❌ エラー: Python 3.13.x が必要です（パッチバージョンは任意）"
    echo "現在のバージョン: $PYTHON_VERSION"
    echo "💡 解決方法:"
    echo "1. pyenv install 3.13"
    echo "2. pyenv local 3.13"
    echo "3. または python3.13 -m venv venv"
    echo ""
    echo "📝 例: 3.13.0, 3.13.1, 3.13.15 などは全て使用可能"
    exit 1
fi

echo "✅ Python バージョン確認: $PYTHON_VERSION"

# OS 検出（sedコマンドの引数調整用）
OS="$(uname -s)"

# 1. .env ファイル作成
if [ ! -f .env ]; then
    if [ ! -f .env.example ]; then
        echo "❌ エラー: .env.example ファイルが見つかりません"
        echo "💡 プロジェクトルートで実行していることを確認してください"
        exit 1
    fi

    echo "📝 .env ファイルを作成しています..."
    cp .env.example .env

    # 開発環境用の安全な初期値を設定
    echo "🔑 開発環境用のランダム値を生成しています..."

    # ランダムなJWT秘密鍵を生成（開発用）
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

    # ランダムなパスワードを生成（開発用）
    DB_PASSWORD=$(python3 -c "import secrets; print('dev_db_' + secrets.token_urlsafe(16))")
    REDIS_PASSWORD=$(python3 -c "import secrets; print('dev_redis_' + secrets.token_urlsafe(16))")

    # プレースホルダーを実際の値に置換（OS別対応）
    if [[ "$OS" == "Darwin" ]]; then
        sed -i '' "s/CHANGE_ME_GENERATE_RANDOM_SECRET_KEY_MINIMUM_32_CHARS/${JWT_SECRET}/" .env
        sed -i '' "s/CHANGE_ME_STRONG_PASSWORD/${DB_PASSWORD}/" .env
        sed -i '' "s/CHANGE_ME_REDIS_PASSWORD/${REDIS_PASSWORD}/" .env
    else
        sed -i "s/CHANGE_ME_GENERATE_RANDOM_SECRET_KEY_MINIMUM_32_CHARS/${JWT_SECRET}/" .env
        sed -i "s/CHANGE_ME_STRONG_PASSWORD/${DB_PASSWORD}/" .env
        sed -i "s/CHANGE_ME_REDIS_PASSWORD/${REDIS_PASSWORD}/" .env
    fi

    echo "✅ .env ファイルが作成されました（開発用ランダム値設定済み）"
    echo "⚠️  本番環境では必ず強力なパスワードに変更してください"
else
    echo "ℹ️  .env ファイルは既に存在します。"
fi

# 2. 環境変数チェック
echo "🔍 環境変数をチェックしています..."
source .env

# 必須変数の存在確認
MISSING_VARS=()
[ -z "$DB_PASSWORD" ] && MISSING_VARS+=("DB_PASSWORD")
[ -z "$REDIS_PASSWORD" ] && MISSING_VARS+=("REDIS_PASSWORD")
[ -z "$JWT_SECRET_KEY" ] && MISSING_VARS+=("JWT_SECRET_KEY")

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo "❌ エラー: 以下の必須環境変数が設定されていません:"
    printf '  %s\n' "${MISSING_VARS[@]}"
    echo "💡 解決方法:"
    echo "  1. .env ファイルを削除して再実行: rm .env && ./scripts/setup.sh"
    echo "  2. または ./scripts/env-check.sh で詳細確認"
    exit 1
fi

# 3. Python仮想環境の作成（ローカル開発用）
if [ ! -d "venv" ]; then
    echo "🐍 Python仮想環境を作成しています..."
    python3 -m venv venv
    echo "✅ 仮想環境が作成されました。"
fi

# 4. 依存関係のインストール（ローカル開発用）
echo "📦 依存関係をインストールしています..."

# 仮想環境のアクティベート確認
if [[ "$VIRTUAL_ENV" == "" ]]; then
    source venv/bin/activate
fi

# requirements ファイルの存在確認
if [ ! -f "requirements/dev.txt" ]; then
    echo "❌ エラー: requirements/dev.txt が見つかりません"
    echo "💡 プロジェクト構成を確認してください"
    exit 1
fi

pip install --upgrade pip
pip install -r requirements/dev.txt

# 5. Pre-commitフックの設定
if command -v pre-commit &> /dev/null; then
    echo "🔧 Pre-commitフックをセットアップしています..."
    pre-commit install
    echo "✅ Pre-commitフックが設定されました。"
else
    echo "⚠️  pre-commit がインストールされていません"
    echo "💡 requirements/dev.txt に pre-commit が含まれているか確認してください"
fi

# 6. VSCode設定確認
if [ -d ".vscode" ]; then
    echo "✅ VSCode設定が検出されました。"
else
    echo "⚠️  VSCode設定フォルダが見つかりません。"
    echo "💡 推奨設定を作成しますか？ (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        mkdir -p .vscode
        echo "📝 基本的なVSCode設定を作成しました。"
    fi
fi

# 7. Docker環境のビルド
echo "🐳 Docker環境をビルドしています..."
if ! docker-compose build; then
    echo "❌ エラー: Docker環境のビルドに失敗しました"
    echo "💡 解決方法:"
    echo "  1. docker-compose.yml ファイルの存在確認"
    echo "  2. Dockerデーモンの起動確認: docker version"
    echo "  3. ディスク容量の確認: df -h"
    exit 1
fi

# 8. データベースとRedisの初期化
echo "🗄️  データベースサービスを起動しています..."
docker-compose up -d db redis

# ヘルスチェック待機
echo "⏳ データベースの起動を待機しています..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker-compose exec -T db pg_isready -U ${DB_USER:-postgres} > /dev/null 2>&1; then
        echo "✅ データベースが利用可能になりました"
        break
    fi
    echo "   待機中... ($((RETRY_COUNT + 1))/$MAX_RETRIES)"
    sleep 2
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "⚠️  データベースの起動確認がタイムアウトしました"
    echo "💡 解決方法:"
    echo "  1. docker-compose logs db でログ確認"
    echo "  2. ポート5432が使用されていないか確認: lsof -i :5432"
    echo "  3. 手動でサービス確認: docker-compose ps"
fi

# 9. データベースマイグレーション（Alembicを使用している場合）
if [ -d "alembic" ] && [ -f "alembic.ini" ]; then
    echo "🔄 データベースマイグレーションを実行しています..."
    if docker-compose exec -T app alembic upgrade head > /dev/null 2>&1; then
        echo "✅ マイグレーションが完了しました"
    else
        echo "⚠️  マイグレーションをスキップします"
        echo "💡 アプリケーション起動後に make migrate を実行してください"
    fi
fi

echo ""
echo "🎉 セットアップが完了しました！"
echo ""
echo "📋 環境構成:"
echo "  Python: $PYTHON_VERSION"
echo "  仮想環境: $(pwd)/venv"
echo "  環境設定: .env (開発用設定)"
echo ""
echo "🚀 次のステップ:"
echo "1. VSCodeでプロジェクトを開く: code ."
echo "2. 推奨拡張機能をインストール (Ctrl+Shift+P → 'Extensions: Show Recommended Extensions')"
echo "3. make docker-up でアプリケーションを起動"
echo "4. http://localhost:8000/docs でAPI仕様を確認"
echo "5. http://localhost:8000/health でヘルスチェック"
echo ""
echo "🛠️  開発コマンド:"
echo "  make help       - 利用可能なコマンド一覧"
echo "  make format     - コードフォーマット"
echo "  make lint       - Lintチェック"
echo "  make test       - テスト実行"
echo "  make all-checks - 全チェック実行"
echo ""
echo "🔒 セキュリティコマンド:"
echo "  ./scripts/env-check.sh     - 環境変数チェック"
echo "  make generate-secrets      - 本番用秘密鍵生成"
echo ""
echo "💡 トラブルシューティング:"
echo "  make docker-logs           - ログ確認"
echo "  make docker-restart        - サービス再起動"
