#!/bin/bash

# 本番環境用の安全な秘密鍵生成スクリプト

echo "🔑 本番環境用の秘密鍵を生成します..."

echo ""
echo "JWT_SECRET_KEY用のランダム文字列（64文字）:"
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

echo ""
echo "データベースパスワード用のランダム文字列（32文字）:"
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

echo ""
echo "Redisパスワード用のランダム文字列（32文字）:"
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

echo ""
echo "⚠️  これらの値を安全な場所に保存し、.envファイルに設定してください"
echo "⚠️  秘密鍵は絶対にGitにコミットしないでください"
