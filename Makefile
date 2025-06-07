.PHONY: help check-python install format lint test test-cov test-auth test-crud test-integrity test-failed test-debug clean docker-build docker-up docker-down docker-test migrate env-check security generate-secrets all-checks

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

# 基本テストコマンド
test: ## 全テストを実行
	pytest tests/ -v

test-cov: ## カバレッジ付きテストを実行
	pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

# 個別テストカテゴリ
test-auth: ## 認証関連テストのみ実行
	pytest tests/test_auth.py -v

test-crud: ## CRUD操作テストのみ実行
	pytest tests/test_tasks_crud.py tests/test_tags_crud.py -v

test-integrity: ## データ整合性テストのみ実行
	pytest tests/test_data_integrity.py -v

# デバッグ・開発用
test-failed: ## 前回失敗したテストのみ再実行
	pytest tests/ --lf -v

test-debug: ## デバッグモードでテスト実行
	pytest tests/ -v -s --tb=long

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

docker-test: ## Docker環境でテスト実行
	docker-compose exec simpletask-backend-api pytest tests/ -v

migrate: ## データベースマイグレーション
	docker-compose exec simpletask-backend-api alembic upgrade head

# 環境・セキュリティチェック
env-check: ## 環境変数チェック
	./scripts/env-check.sh

security: ## セキュリティチェック
	pip-audit
	bandit -r app/

generate-secrets: ## 本番用秘密鍵生成
	./scripts/generate-secrets.sh

# 総合チェック
all-checks: lint test security ## 全チェックを実行
