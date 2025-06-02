#!/bin/bash

# 開発環境管理スクリプト

set -e

COMMAND=${1:-help}

case $COMMAND in
    "start")
        echo "🚀 開発環境を起動しています..."
        docker-compose up -d
        echo "✅ 起動完了"
        echo "API: http://localhost:8000"
        echo "API Docs: http://localhost:8000/docs"
        ;;
    "stop")
        echo "🛑 開発環境を停止しています..."
        docker-compose down
        echo "✅ 停止完了"
        ;;
    "restart")
        echo "🔄 開発環境を再起動しています..."
        docker-compose down
        docker-compose up -d
        echo "✅ 再起動完了"
        ;;
    "logs")
        SERVICE=${2:-api}
        echo "📋 ${SERVICE}のログを表示..."
        docker-compose logs -f $SERVICE
        ;;
    "shell")
        echo "🐚 APIコンテナのシェルに接続..."
        docker-compose exec api bash
        ;;
    "db")
        echo "🗄️  データベースに接続..."
        docker-compose exec db psql -U postgres -d simpletask
        ;;
    "redis")
        echo "🔴 Redisに接続..."
        docker-compose exec redis redis-cli
        ;;
    "clean")
        echo "🧹 Docker環境をクリーンアップ..."
        docker-compose down -v
        docker system prune -f
        echo "✅ クリーンアップ完了"
        ;;
    "help"|*)
        echo "🛠️  SimpleTask Backend 開発ツール"
        echo ""
        echo "使用方法: $0 <command>"
        echo ""
        echo "コマンド:"
        echo "  start    - 開発環境を起動"
        echo "  stop     - 開発環境を停止"
        echo "  restart  - 開発環境を再起動"
        echo "  logs     - ログを表示 (service名を指定可能)"
        echo "  shell    - APIコンテナのシェルに接続"
        echo "  db       - データベースに接続"
        echo "  redis    - Redisに接続"
        echo "  clean    - Docker環境をクリーンアップ"
        echo "  help     - このヘルプを表示"
        ;;
esac
