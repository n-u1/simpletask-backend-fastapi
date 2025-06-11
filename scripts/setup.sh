#!/bin/bash

# SimpleTask Backend セットアップスクリプト

set -e

readonly DEFAULT_PYTHON_VERSION="3.13.4"

echo "🚀 SimpleTask Backend セットアップを開始します..."

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

check_python_version() {
    echo "🔍 Python バージョンを確認しています..."

    # .python-versionファイルから要求バージョンを取得
    if [ -f ".python-version" ]; then
        REQUIRED_VERSION=$(cat .python-version | tr -d '\n\r')
        echo "   要求バージョン: $REQUIRED_VERSION (.python-versionより)"
    else
        REQUIRED_VERSION="$DEFAULT_PYTHON_VERSION"
        echo "   要求バージョン: $REQUIRED_VERSION (デフォルト)"
    fi

    # pyenvの存在確認
    if command -v pyenv &> /dev/null; then
        handle_pyenv_environment "$REQUIRED_VERSION"
    else
        handle_non_pyenv_environment "$REQUIRED_VERSION"
    fi
}

# pyenv環境での処理
handle_pyenv_environment() {
    local required_version="$1"

    echo "🔧 pyenv環境を検出しました"

    # pyenvに要求バージョンがインストールされているかチェック
    if pyenv versions --bare | grep -q "^${required_version}$"; then
        echo "✅ Python $required_version はpyenvにインストール済みです"

        # .python-versionファイルに基づいてローカル設定
        if [ -f ".python-version" ]; then
            echo "📝 .python-versionファイルに基づいてローカル設定を適用しています..."
            pyenv local "$required_version"
        fi

        # 現在のPythonバージョンを確認
        CURRENT_VERSION=$(python3 --version 2>/dev/null | cut -d' ' -f2 || echo "unknown")

        if [ "$CURRENT_VERSION" = "$required_version" ]; then
            echo "✅ Python バージョン確認: $CURRENT_VERSION"
            return 0
        else
            echo "⚠️  設定後も異なるバージョンが適用されています"
            echo "   現在: $CURRENT_VERSION, 期待: $required_version"
            echo "   pyenv管理: $(pyenv which python3 2>/dev/null || echo 'エラー')"

            # PATH問題の可能性を判定
            if [[ "$(which python3)" != *".pyenv"* ]]; then
                echo ""
                show_pyenv_path_fix_guide "$required_version"
            else
                show_pyenv_troubleshooting
            fi
            exit 1
        fi
    else
        echo "❌ Python $required_version がpyenvにインストールされていません"
        offer_pyenv_install_guide "$required_version"
        exit 1
    fi
}

# pyenvのPATH設定修正ガイド
show_pyenv_path_fix_guide() {
    local required_version="$1"

    echo "⚠️  pyenvのPATH設定に問題があります"
    echo ""
    echo "📋 現在の状況："
    echo "   システムのpython3: $(which python3)"
    echo "   pyenv管理のpython3: $(pyenv which python3 2>/dev/null || echo '設定されていません')"
    echo "   現在のバージョン: $(python3 --version | cut -d' ' -f2)"
    echo "   期待するバージョン: $required_version"
    echo ""

    # シェル設定ファイルを特定
    if [[ "$SHELL" == *"zsh"* ]]; then
        CONFIG_FILE="$HOME/.zshrc"
        SHELL_NAME="zsh"
    elif [[ "$SHELL" == *"bash"* ]]; then
        CONFIG_FILE="$HOME/.bashrc"
        SHELL_NAME="bash"
    else
        CONFIG_FILE="$HOME/.profile"
        SHELL_NAME="shell"
    fi

    # 既存設定の確認
    if grep -q "pyenv init" "$CONFIG_FILE" 2>/dev/null; then
        echo "ℹ️  $CONFIG_FILE に既存のpyenv設定が見つかりました："
        echo ""
        grep -n "pyenv" "$CONFIG_FILE" | sed 's/^/   /'
        echo ""
        echo "🤔 既存設定があるにも関わらず問題が発生しています"
        echo ""
        echo "💡 解決方法："
        echo "   1. 新しいターミナルを開いて再実行してください"
        echo "   2. または設定を手動で確認・修正してください"
        echo ""
        show_manual_pyenv_check "$CONFIG_FILE"
    else
        echo "💡 pyenvのPATH設定が $CONFIG_FILE に見つかりません"
        echo ""
        show_manual_pyenv_setup "$CONFIG_FILE" "$SHELL_NAME" "$required_version"
    fi
}

# pyenvインストールガイド
offer_pyenv_install_guide() {
    local required_version="$1"

    echo ""
    echo "📦 Python $required_version のインストールが必要です"
    echo ""
    echo "🔧 インストールと設定："
    echo "   pyenv install $required_version"
    echo "   pyenv local $required_version"
    echo ""
    echo "⏱️  インストールには数分かかる場合があります"
    echo ""
    echo "💡 インストール後、スクリプトを再実行してください"
}

# 手動pyenv設定ガイド
show_manual_pyenv_setup() {
    local config_file="$1"
    local shell_name="$2"
    local required_version="$3"

    echo "🔧 手動設定方法："
    echo ""
    echo "1. $config_file を編集："
    echo "   # テキストエディタで開く（編集できれば何でも可）"
    echo "   code $config_file          # VS Code"
    echo "   nano $config_file          # ターミナルエディタ"
    echo ""
    echo "2. ファイルの末尾に以下を追加："
    echo ""
    echo "   # pyenv設定"
    echo "   export PATH=\"\$HOME/.pyenv/bin:\$PATH\""
    echo "   eval \"\$(pyenv init --path)\""
    echo "   eval \"\$(pyenv init -)\""
    echo ""
    echo "3. 設定を適用："
    echo "   source $config_file"
    echo ""
    echo "4. バージョン確認："
    echo "   python3 --version  # $required_version と表示されるはず"
    echo ""
    echo "💡 設定後、スクリプトを再実行してください"
}

# pyenv設定確認ガイド
show_manual_pyenv_check() {
    local config_file="$1"

    echo "🔍 設定確認方法："
    echo ""
    echo "1. 現在の設定確認："
    echo "   cat $config_file | grep pyenv"
    echo ""
    echo "2. PATH確認："
    echo "   echo \$PATH | grep pyenv"
    echo ""
    echo "3. pyenv動作確認："
    echo "   pyenv version"
    echo "   pyenv which python3"
    echo ""
    echo "4. 必要に応じて設定を修正："
    echo "   code $config_file  # エディタで開いて確認・修正"
}

# pyenv環境でのトラブルシューティング
show_pyenv_troubleshooting() {
    echo ""
    echo "🔧 問題の確認方法："
    echo "   pyenv --version"
    echo "   pyenv which python3"
    echo "   echo \$PATH | grep pyenv"
    echo ""
    echo "💡 手動で設定を確認してください"
}

# 非pyenv環境での処理
handle_non_pyenv_environment() {
    local required_version="$1"

    echo "ℹ️  pyenvが検出されませんでした"

    # Pythonコマンドの存在確認
    if ! command -v python3 &> /dev/null; then
        echo "❌ エラー: python3 コマンドが見つかりません"
        show_python_install_guide "$required_version"
        exit 1
    fi

    # 現在のバージョン取得・チェック
    CURRENT_VERSION=$(python3 --version 2>/dev/null | cut -d' ' -f2 || echo "unknown")

    if [ "$CURRENT_VERSION" != "$required_version" ]; then
        echo "❌ エラー: Python バージョンが一致しません"
        echo "   現在のバージョン: $CURRENT_VERSION"
        echo "   必要なバージョン: $required_version"
        echo ""
        show_python_install_guide "$required_version"
        exit 1
    fi

    echo "✅ Python バージョン確認: $CURRENT_VERSION"
}

# 非pyenv環境でのインストールガイド
show_python_install_guide() {
    local required_version="$1"

    echo "🔧 Python $required_version のインストール方法:"
    echo ""
    echo "1️⃣ pyenv使用（推奨 - 正確なバージョン指定が可能）:"
    echo "   # pyenvインストール"
    echo "   curl https://pyenv.run | bash"
    echo "   # または"
    echo "   brew install pyenv                    # macOS"
    echo "   sudo apt install pyenv                # Ubuntu"
    echo ""
    echo "   # シェル設定追加 (~/.bashrc または ~/.zshrc)"
    echo "   export PATH=\"\$HOME/.pyenv/bin:\$PATH\""
    echo "   eval \"\$(pyenv init --path)\""
    echo "   eval \"\$(pyenv init -)\""
    echo ""
    echo "   # シェル再起動後"
    echo "   pyenv install $required_version"
    echo "   pyenv local $required_version"
    echo ""
    echo "2️⃣ 公式インストーラー（正確なバージョン指定）:"
    echo "   https://www.python.org/downloads/release/python-${required_version//./}/"
    echo ""
    echo "3️⃣ Docker環境使用（Pythonインストール不要）:"
    echo "   make docker-dev    # 開発用コンテナで作業"
    echo ""
    echo "⚠️  重要な注意事項:"
    echo "   - パッケージマネージャーではパッチバージョンを指定できません"
    echo "   - 完全一致が必要な場合は、pyenvまたは公式インストーラーを使用してください"
    echo "   - システムパッケージを使用した場合は必ずバージョンを確認してください"
    echo ""
    echo "💡 チーム開発では pyenv の使用を強く推奨します（全員が同じバージョンを使用可能）"
}

# .python-versionファイルの存在確認
ensure_python_version_file() {
    if [ ! -f ".python-version" ]; then
        echo "📝 .python-versionファイルを作成しています..."
        echo "$DEFAULT_PYTHON_VERSION" > .python-version
        echo "✅ .python-versionファイルが作成されました"
    else
        # 既存ファイルのバージョンが古い場合は更新提案
        CURRENT_FILE_VERSION=$(cat .python-version | tr -d '\n\r')
        if [ "$CURRENT_FILE_VERSION" != "$DEFAULT_PYTHON_VERSION" ]; then
            echo "ℹ️  .python-versionファイル: $CURRENT_FILE_VERSION"
            echo "💡 Python $DEFAULT_PYTHON_VERSION が利用可能です"
            echo ""
            echo "🔄 $DEFAULT_PYTHON_VERSION に更新しますか？ (y/N)"
            read -r response
            if [[ "$response" =~ ^[Yy]$ ]]; then
                echo "$DEFAULT_PYTHON_VERSION" > .python-version
                echo "✅ .python-versionを$DEFAULT_PYTHON_VERSION に更新しました"
            else
                echo "ℹ️  現在のバージョン($CURRENT_FILE_VERSION)を維持します"
            fi
        fi
    fi
}

# 必要なコマンドの存在確認
echo "🔍 必要なツールの確認..."
check_command "docker"
check_command "docker-compose"
check_command "git"

# Python環境の確認
ensure_python_version_file
check_python_version

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
docker-compose up -d simpletask-backend-db simpletask-backend-redis

# ヘルスチェック待機
echo "⏳ データベースの起動を待機しています..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker-compose exec -T simpletask-backend-db pg_isready -U ${DB_USER:-postgres} > /dev/null 2>&1; then
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
    echo "  1. docker-compose logs simpletask-backend-db でログ確認"
    echo "  2. ポート5432が使用されていないか確認: lsof -i :5432"
    echo "  3. 手動でサービス確認: docker-compose ps"
fi

# 9. データベースマイグレーション
if [ -d "alembic" ] && [ -f "alembic.ini" ]; then
    echo "🔄 データベースマイグレーションを実行しています..."
    if docker-compose exec -T simpletask-backend-api alembic upgrade head > /dev/null 2>&1; then
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
CURRENT_PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "  Python: $CURRENT_PYTHON_VERSION"
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
