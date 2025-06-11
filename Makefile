.PHONY: help setup check-python install format lint test test-cov test-auth test-crud test-integrity test-failed test-debug clean docker-build docker-up docker-down docker-test migrate env-check security generate-secrets all-checks

help: ## ヘルプを表示
	@echo "利用可能なコマンド:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# セットアップ関連
setup: ## 初回環境セットアップ
	@echo "🚀 初回環境セットアップを開始します..."
	@chmod +x scripts/setup.sh
	@./scripts/setup.sh

check-python: ## Pythonバージョンチェック
	@if [ -f ".python-version" ]; then \
		REQUIRED_VERSION=$$(cat .python-version | tr -d '\n\r'); \
	else \
		REQUIRED_VERSION="3.13.4"; \
	fi; \
	CURRENT_VERSION=$$(python3 --version 2>/dev/null | cut -d' ' -f2 || echo "not found"); \
	if [ "$$CURRENT_VERSION" != "$$REQUIRED_VERSION" ]; then \
		echo "❌ Python バージョンが一致しません"; \
		echo "   現在: $$CURRENT_VERSION"; \
		echo "   要求: $$REQUIRED_VERSION"; \
		echo "💡 解決方法: make setup を実行してください"; \
		exit 1; \
	fi; \
	echo "✅ Python バージョンOK ($$CURRENT_VERSION)"

install: ## 依存関係をインストール
	./venv/bin/pip install -r requirements/dev.txt
	./venv/bin/pre-commit install

format: ## コードをフォーマット
	./venv/bin/ruff format app/ tests/
	./venv/bin/ruff --fix app/ tests/

lint: ## Lintチェックを実行
	./venv/bin/ruff check app/ tests/
	./venv/bin/mypy app/
	./venv/bin/bandit -r app/

# 基本テストコマンド
test: ## 全テストを実行
	./venv/bin/pytest tests/ -v

test-cov: ## カバレッジ付きテストを実行
	./venv/bin/pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

# 個別テストカテゴリ
test-auth: ## 認証関連テストのみ実行
	./venv/bin/pytest tests/test_auth.py -v

test-crud: ## CRUD操作テストのみ実行
	./venv/bin/pytest tests/test_tasks_crud.py tests/test_tags_crud.py -v

test-integrity: ## データ整合性テストのみ実行
	./venv/bin/pytest tests/test_data_integrity.py -v

# デバッグ・開発用
test-failed: ## 前回失敗したテストのみ再実行
	./venv/bin/pytest tests/ --lf -v

test-debug: ## デバッグモードでテスト実行
	./venv/bin/pytest tests/ -v -s --tb=long

clean: ## キャッシュファイルを削除
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov/ reports/

# Docker関連
docker-build: ## Dockerイメージをビルド
	docker-compose build

docker-up: ## Docker環境を起動
	docker-compose up -d

docker-down: ## Docker環境を停止
	docker-compose down

docker-restart: ## Docker環境を再起動
	@$(MAKE) docker-down
	@$(MAKE) docker-up

docker-logs: ## Dockerログを表示
	docker-compose logs -f

docker-test: ## Docker環境でテスト実行
	docker-compose exec simpletask-backend-api pytest tests/ -v

migrate: ## データベースマイグレーション
	docker-compose exec simpletask-backend-api alembic upgrade head

# 環境・セキュリティチェック
env-check: ## 環境変数チェック
	./scripts/env-check.sh

security: ## セキュリティチェック
	./venv/bin/pip-audit
	./venv/bin/bandit -r app/

generate-secrets: ## 本番用秘密鍵生成
	./scripts/generate-secrets.sh

# 総合チェック
all-checks: lint test security ## 全チェックを実行

# 開発フロー
dev: docker-up ## 開発環境を起動
	@echo "🚀 開発環境が起動しました"
	@echo "📖 API仕様: http://localhost:8000/docs"
	@echo "❤️ ヘルスチェック: http://localhost:8000/health"

reset: ## 開発環境をリセット
	@echo "⚠️  開発環境をリセットします（データも削除されます）"
	@read -p "続行しますか？ [y/N]: " confirm && [ "$$confirm" = "y" ]
	@$(MAKE) docker-down
	@docker-compose down -v
	@$(MAKE) clean
	@echo "✅ 開発環境がリセットされました"
	@echo "💡 再セットアップは 'make setup' を実行してください"
