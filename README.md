# SimpleTask Backend

個人タスク管理のための Web アプリケーション「SimpleTask」の REST API（バックエンド）です。

## 🎯 プロジェクト概要

Python を使ったモダンなバックエンド開発を行う個人プロジェクトです。  
業務で Python を使用する機会がないため、触れてみることを目的としています。

### プロジェクトの方針

- 個人開発ではあるが実務も意識した開発を行う
- 技術スタックは一般的なもの・勢いのあるものから選定する
- プロジェクトの趣旨に照らし、Python とそのフレームワークを使用する
- フロントエンドとバックエンドは分離した構成とし、当リポジトリではフロントエンドは実装しない
- API については REST 形式とし、OpenAPI 仕様でドキュメント化する
- CRUD 操作やデータ整合性などクリティカルになりそうな部分はテストを記述する

### アプリケーションの選定基準

- 個人プロジェクトとしてちょうどよい規模感であること（大き過ぎず小さ過ぎない）
- 一般的なシステムで求められる基本機能が含まれること（CRUD 操作や認証、リソースアクセス制御等）
- 今後の拡張性やカスタマイズ性があること（当初段階では機能を絞る想定のため）

### アプリケーションの主な機能

- **ユーザー認証** - JWT トークンベース認証
- **タスク管理** - CRUD 操作、ステータス管理、優先度設定
- **タグ機能** - タスクの分類・検索機能
- **カンバンボード対応** - ドラッグ&ドロップによる並び替え

## 🛠 技術スタック

### Backend

- **FastAPI** - 高速でモダンな Python Web フレームワーク
- **SQLAlchemy** - 非同期対応の ORM
- **PostgreSQL** - メインデータベース
- **Redis** - セッション管理・キャッシュ
- **Alembic** - データベースマイグレーション
- **Pydantic** - データバリデーション

### Development & Infrastructure

- **Docker** - コンテナ化
- **pytest** - テストフレームワーク
- **Ruff** - Linter & Formatter
- **mypy** - 型チェック
- **pre-commit** - Git フック管理

## 🏗 アーキテクチャ

レイヤードアーキテクチャによる関心の分離

- **API 層** → **Service 層** → **CRUD 層** → **Model 層**
- FastAPI による OpenAPI 仕様ドキュメントの自動生成
- フロントエンド・バックエンド分離（想定は SPA + API 構成）

## 🚀 クイックスタート

### 前提条件

- **Python 3.13.3**
- **Docker & Docker Compose**
- **Git**
- **pyenv**

### セットアップ

```bash
# リポジトリをクローン
git clone https://github.com/n-u1/simpletask-backend-fastapi.git
cd simpletask-backend-fastapi

# 環境セットアップ・起動
make setup
make docker-up

# 動作確認
# API仕様: http://localhost:8000/docs
# ヘルスチェック: http://localhost:8000/health
```

### 🎉 完了

正常に処理が完了すると開発環境が起動します

---

### 環境別の実行方法

**Windows (make コマンドが使えない場合):**

```bash
bash scripts/setup.sh
docker-compose up -d
```

### トラブルシューティング

**Python 3.13 エラー** → `pyenv install 3.13 && pyenv local 3.13`  
**Docker エラー** → [Docker Desktop](https://docs.docker.com/get-docker/) をインストール  
**ポート 8000 エラー** → `lsof -i :8000` で使用中プロセス確認  
**その他** → `make docker-logs` でログ確認

## 📚 API

### 認証

```bash
POST /api/v1/auth/register  # ユーザー登録
POST /api/v1/auth/login     # ログイン・JWT取得
```

### タスク

```bash
GET    /api/v1/tasks                    # 一覧取得（フィルタ・ソート対応）
POST   /api/v1/tasks                    # 作成
PATCH  /api/v1/tasks/reorder           # カンバンボード並び替え
```

詳細: http://localhost:8000/docs

## 🧪 開発

```bash
make install     # 依存関係インストール
make format      # コードフォーマット
make test        # テスト実行
make help        # コマンド一覧
```

## 🎓 その他

### 実務を意識した取り組み

- レイヤー化による保守性を意識した設計
- setup.sh + Makefile を用いた環境構築や操作の効率化
- Docker による環境統一
