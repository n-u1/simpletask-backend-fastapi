#!/bin/bash

# SimpleTask Backend セットアップスクリプト

set -e

echo "🚀 SimpleTask Backend セットアップを開始します..."

# Python バージョンチェック
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
REQUIRED_VERSION="3.13"

if [[ ! "$PYTHON_VERSION" =~ ^3\.13\. ]]; then
    echo "❌ エラー: Python 3.13が必要です"
    echo "現在のバージョン: $PYTHON_VERSION"
    echo "💡 解決方法:"
    echo "1. pyenv install 3.13"
    echo "2. pyenv local 3.13"
    echo "3. または python3.13 -m venv venv"
    exit 1
fi

echo "✅ Python バージョン確認: $PYTHON_VERSION"

# 1. .env ファイル作成
if [ ! -f .env ]; then
    echo "📝 .env ファイルを作成しています..."
    cp .env.example .env

    # 開発環境用の安全な初期値を設定
    echo "🔑 開発環境用のランダム値を生成しています..."

    # ランダムなJWT秘密鍵を生成（開発用）
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

    # ランダムなパスワードを生成（開発用）
    DB_PASSWORD=$(python3 -c "import secrets; print('dev_db_' + secrets.token_urlsafe(16))")
    REDIS_PASSWORD=$(python3 -c "import secrets; print('dev_redis_' + secrets.token_urlsafe(16))")

    # プレースホルダーを実際の値に置換
    sed -i.bak "s/CHANGE_ME_GENERATE_RANDOM_SECRET_KEY_MINIMUM_32_CHARS/${JWT_SECRET}/" .env
    sed -i.bak "s/CHANGE_ME_STRONG_PASSWORD/${DB_PASSWORD}/" .env
    sed -i.bak "s/CHANGE_ME_REDIS_PASSWORD/${REDIS_PASSWORD}/" .env

    # バックアップファイルを削除
    rm -f .env.bak

    echo "✅ .env ファイルが作成されました（開発用ランダム値設定済み）"
    echo "⚠️  本番環境では必ず強力なパスワードに変更してください"
else
    echo "ℹ️  .env ファイルは既に存在します。"
fi

# 2. 環境変数チェック
echo "🔍 環境変数をチェックしています..."
source .env

# 必須変数の存在確認
if [ -z "$DB_PASSWORD" ] || [ -z "$REDIS_PASSWORD" ] || [ -z "$JWT_SECRET_KEY" ]; then
    echo "❌ エラー: 必須環境変数が設定されていません"
    echo "💡 ./scripts/env-check.sh を実行して詳細を確認してください"
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
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements/dev.txt

# 5. Pre-commitフックの設定
echo "🔧 Pre-commitフックをセットアップしています..."
pre-commit install
echo "✅ Pre-commitフックが設定されました。"

# 6. VSCode設定確認
if [ -d ".vscode" ]; then
    echo "✅ VSCode設定が検出されました。"
else
    echo "⚠️  VSCode設定フォルダが見つかりません。.vscode/フォルダを作成してください。"
fi

# 7. Docker環境のビルド
echo "🐳 Docker環境をビルドしています..."
docker-compose build

# 8. データベースとRedisの初期化
echo "🗄️  データベースサービスを起動しています..."
docker-compose up -d db redis

# ヘルスチェック待機
echo "⏳ データベースの起動を待機しています..."
sleep 10

echo "✅ セットアップが完了しました！"
echo ""
echo "🎉 次のステップ:"
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
