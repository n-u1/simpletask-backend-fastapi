#!/bin/bash

# 開発環境管理スクリプト

set -e

COMMAND=${1:-help}

case $COMMAND in
    "start")
        echo "🚀 開発環境を起動しています..."
        docker-compose up -d
        echo "✅ 起動完了"
        echo "📖 API: http://localhost:8000"
        echo "📋 API Docs: http://localhost:8000/docs"
        echo "❤️  Health: http://localhost:8000/health"
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
        SERVICE=${2:-simpletask-backend-api}
        echo "📋 ${SERVICE}のログを表示..."
        docker-compose logs -f $SERVICE
        ;;
    "shell")
        echo "🐚 APIコンテナのシェルに接続..."
        docker-compose exec simpletask-backend-api bash
        ;;
    "db")
        echo "🗄️  データベースに接続..."
        docker-compose exec simpletask-backend-db psql -U postgres -d simpletask
        ;;
    "redis")
        echo "🔴 Redisに接続..."
        # 環境変数を読み込んでパスワード認証付きで接続
        source .env 2>/dev/null || echo "⚠️ .envファイルが読み込めません"
        docker-compose exec simpletask-backend-redis redis-cli -a "${REDIS_PASSWORD}"
        ;;
    "status")
        echo "📊 サービス状況を確認..."
        docker-compose ps
        echo ""
        echo "🌐 エンドポイント確認:"
        if command -v jq &> /dev/null; then
            curl -s http://localhost:8000/health | jq '.' 2>/dev/null || echo "❌ API応答なし"
        else
            curl -s http://localhost:8000/health 2>/dev/null || echo "❌ API応答なし"
            echo "💡 jqをインストールするとJSON出力が見やすくなります"
        fi
        ;;
    "update")
        echo "🔄 依存関係を更新..."
        # 仮想環境がアクティブでない場合はアクティベート
        if [[ "$VIRTUAL_ENV" == "" ]]; then
            source venv/bin/activate
        fi
        pip install --upgrade pip
        pip install -r requirements/dev.txt --upgrade
        docker-compose build --no-cache
        echo "✅ 更新完了"
        ;;
    "backup")
        BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
        echo "💾 データベースをバックアップ中..."
        mkdir -p "$BACKUP_DIR"
        docker-compose exec -T simpletask-backend-db pg_dump -U postgres simpletask > "$BACKUP_DIR/simpletask.sql"
        echo "✅ バックアップ完了: $BACKUP_DIR/simpletask.sql"
        ;;
    "clean")
        echo "🧹 Docker環境をクリーンアップ..."
        read -p "⚠️  全データが削除されます。続行しますか？ (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose down -v
            docker system prune -f
            echo "✅ クリーンアップ完了"
        else
            echo "❌ キャンセルされました"
        fi
        ;;
    "help"|*)
        echo "🛠️  SimpleTask Backend 開発ツール"
        echo ""
        echo "使用方法: $0 <command>"
        echo ""
        echo "📋 利用可能なコマンド:"
        echo "  start     - 開発環境を起動"
        echo "  stop      - 開発環境を停止"
        echo "  restart   - 開発環境を再起動"
        echo "  logs      - ログを表示 (service名を指定可能)"
        echo "  shell     - APIコンテナのシェルに接続"
        echo "  db        - データベースに接続"
        echo "  redis     - Redisに接続"
        echo "  status    - サービス状況確認"
        echo "  clean     - Docker環境をクリーンアップ"
        echo "  update    - 依存関係とDockerイメージを更新"
        echo "  backup    - データベースをバックアップ"
        echo "  help      - このヘルプを表示"
        echo ""
        echo "📖 例:"
        echo "  $0 start                    # 開発環境起動"
        echo "  $0 logs simpletask-backend-db    # DBサービスのログ表示"
        echo "  $0 shell                    # コンテナ内でコマンド実行"
        echo "  $0 backup                   # データベースバックアップ"
        echo ""
        echo "📋 利用可能なサービス名:"
        echo "  - simpletask-backend-api"
        echo "  - simpletask-backend-db"
        echo "  - simpletask-backend-redis"
        ;;
esac
