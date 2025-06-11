#!/bin/bash

# Python バージョンチェック
check_python_version() {
    echo "🔍 Python バージョンを確認しています..."

    # .python-versionファイルから要求バージョンを取得
    if [ -f ".python-version" ]; then
        REQUIRED_VERSION=$(cat .python-version | tr -d '\n\r')
        echo "   要求バージョン: $REQUIRED_VERSION (.python-versionより)"
    else
        REQUIRED_VERSION="3.13.3"
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
            echo "⚠️  設定後も異なるバージョンが選択されています"
            echo "   現在: $CURRENT_VERSION, 期待: $required_version"
            echo "💡 以下を確認してください:"
            echo "   - pyenv which python3"
            echo "   - pyenv version"
            echo "   - echo \$PATH"
        fi
    else
        echo "❌ Python $required_version がpyenvにインストールされていません"
        offer_pyenv_install "$required_version"
    fi
}

# pyenvでのインストール提案
offer_pyenv_install() {
    local required_version="$1"

    echo ""
    echo "🤖 Python $required_version を自動でインストールしますか？ (y/N)"
    echo "   ⚠️  インストールには数分かかる場合があります"

    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo ""
        echo "📦 Python $required_version をインストールしています..."

        # インストール可能かチェック
        if ! pyenv install --list | grep -q "^\s*$required_version$"; then
            echo "❌ エラー: Python $required_version が利用できません"
            echo "💡 利用可能なバージョン確認: pyenv install --list | grep 3.13"
            echo "💡 pyenvアップデート: pyenv update または brew upgrade pyenv"
            exit 1
        fi

        # インストール実行
        echo "   開始時刻: $(date)"
        if pyenv install "$required_version"; then
            pyenv local "$required_version"
            echo "✅ Python $required_version のインストールが完了しました"
            echo "   完了時刻: $(date)"

            # インストール後の確認
            CURRENT_VERSION=$(python3 --version 2>/dev/null | cut -d' ' -f2 || echo "unknown")
            if [ "$CURRENT_VERSION" = "$required_version" ]; then
                echo "✅ バージョン確認: $CURRENT_VERSION"
                return 0
            else
                echo "⚠️  インストール後も期待したバージョンになっていません"
                echo "   現在: $CURRENT_VERSION, 期待: $required_version"
                troubleshoot_pyenv
                exit 1
            fi
        else
            echo "❌ エラー: Python $required_version のインストールに失敗しました"
            echo "💡 トラブルシューティング:"
            echo "   - ディスク容量確認: df -h"
            echo "   - ログ確認: ~/.pyenv/versions/$required_version/build.log"
            echo "   - 手動インストール: pyenv install $required_version -v"
            exit 1
        fi
    else
        echo ""
        echo "❌ Python $required_version のインストールが必要です"
        show_pyenv_manual_guide "$required_version"
        exit 1
    fi
}

# pyenv環境でのトラブルシューティング
troubleshoot_pyenv() {
    echo ""
    echo "🔧 pyenvトラブルシューティング:"
    echo "1. シェル設定確認:"
    echo "   echo \$PATH | grep pyenv"
    echo "   pyenv --version"
    echo ""
    echo "2. 現在の設定確認:"
    echo "   pyenv version"
    echo "   pyenv which python3"
    echo ""
    echo "3. シェル再起動:"
    echo "   exec \$SHELL"
    echo ""
    echo "4. pyenv初期化確認 (~/.bashrc または ~/.zshrc):"
    echo "   export PATH=\"\$HOME/.pyenv/bin:\$PATH\""
    echo "   eval \"\$(pyenv init --path)\""
    echo "   eval \"\$(pyenv init -)\""
}

# pyenv手動ガイド
show_pyenv_manual_guide() {
    local required_version="$1"
    echo "🔧 手動でのインストール方法:"
    echo "   pyenv install $required_version"
    echo "   pyenv local $required_version"
    echo ""
    echo "💡 インストール後、再度このスクリプトを実行してください"
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
        echo "3.13.3" > .python-version
        echo "✅ .python-versionファイルが作成されました"
    fi
}

ensure_python_version_file
check_python_version
