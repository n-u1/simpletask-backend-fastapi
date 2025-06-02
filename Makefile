.PHONY: help check-python install format lint test test-cov clean docker-build docker-up docker-down migrate

help: ## ヘルプを表示
	@echo "利用可能なコマンド:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

check-python: ## Pythonバージョンチェック
	@python --version | grep -q "Python 3.13" || (echo "❌ Python 3.13が必要です" && exit 1)
	@echo "✅ Python バージョンOK"

install: ## 依存関係をインストール
	pip install -r requirements/dev.txt
	pre-commit install

format: ## コードをフォーマット
	ruff format app/ tests/
	ruff --fix app/ tests/

lint: ## Lintチェックを実行
	ruff check app/ tests/
	mypy app/
	bandit -r app/

test: ## テストを実行
	pytest tests/ -v

test-cov: ## カバレッジ付きテストを実行
	pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

clean: ## キャッシュファイルを削除
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov/

docker-build: ## Dockerイメージをビルド
	docker-compose build

docker-up: ## Docker環境を起動
	docker-compose up -d

docker-down: ## Docker環境を停止
	docker-compose down

migrate: ## データベースマイグレーション
	docker-compose exec api alembic upgrade head

env-check: ## 環境変数チェック
	./scripts/env-check.sh

security: ## セキュリティチェック
	pip-audit
	bandit -r app/

security-full: ## 完全なセキュリティチェック
	./scripts/security-check.sh

generate-secrets: ## 本番用秘密鍵生成
	./scripts/generate-secrets.sh

all-checks: format lint test security ## 全チェックを実行
