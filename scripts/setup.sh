#!/bin/bash

check_python_version() {
    echo "🔍 Python バージョンを確認しています..."

    # .python-versionファイルから要求バージョンを取得
    if [ -f ".python-version" ]; then
        REQUIRED_VERSION=$(cat .python-version | tr -d '\n\r')
        echo "   要求バージョン: $REQUIRED_VERSION (.python-versionより)"
    else
        REQUIRED_VERSION="3.13.4"
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
    echo "🔧 インストール方法："
    echo "   pyenv install $required_version"
    echo "   pyenv local $required_version"
    echo ""
    echo "⏱️  インストールには数分かかる場合があります"
    echo ""
    echo "💡 インストール後、このスクリプトを再実行してください"
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
    echo "   code $config_file          # VS Codeの場合"
    echo "   nano $config_file          # ターミナルエディタの場合"
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
        echo "3.13.4" > .python-version
        echo "✅ .python-versionファイルが作成されました"
    else
        # 既存ファイルのバージョンが古い場合は更新提案
        CURRENT_FILE_VERSION=$(cat .python-version | tr -d '\n\r')
        if [ "$CURRENT_FILE_VERSION" != "3.13.4" ]; then
            echo "ℹ️  .python-versionファイル: $CURRENT_FILE_VERSION"
            echo "💡 Python 3.13.4 が利用可能です"
            echo ""
            echo "🔄 3.13.4 に更新しますか？ (y/N)"
            read -r response
            if [[ "$response" =~ ^[Yy]$ ]]; then
                echo "3.13.4" > .python-version
                echo "✅ .python-versionを3.13.4に更新しました"
            else
                echo "ℹ️  現在のバージョン($CURRENT_FILE_VERSION)を維持します"
            fi
        fi
    fi
}

echo "🚀 SimpleTask Backend Python環境セットアップ"
echo ""

ensure_python_version_file
check_python_version

echo ""
echo "✅ Python環境の確認が完了しました!"
