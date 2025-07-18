# SimpleTask Backend

Web アプリケーション「SimpleTask」の REST API（バックエンド）です。  
個人タスク管理用のアプリケーションを想定しています。

## 🎯 プロジェクト概要

Python（FastAPI）を用いたモダンなバックエンド開発を試行する個人プロジェクトです。  
業務で Python を使用する機会がないため、実際に触れながら理解を深めることを目的としています。

### プロジェクトの方針

- プロジェクトの趣旨に照らし、Python と FastAPI を使用する
- その他の技術スタックは一般的なもの・勢いのあるものから選定する
- 個人開発ではあるが実務も意識した開発を行う
- フロントエンドとバックエンドは分離した構成とし、当リポジトリではフロントエンドは実装しない
- API については REST 形式とし、OpenAPI 仕様でドキュメント化する
- CRUD 操作やデータ整合性などクリティカルになりそうな部分はテストを記述する

### アプリケーションの選定基準

- 個人プロジェクトとしてちょうどよい規模感であること（大き過ぎず小さ過ぎない）
- 機能は絞るが一般的なシステムで求められる基本機能は含まれること（CRUD 操作や認証など）
- 拡張性やカスタマイズ性があること（あとから機能拡張する可能性もあるため）

### アプリケーションの主な機能

- **ユーザー認証** - JWT トークンベース認証
- **タスク管理** - CRUD 操作、ステータス管理、優先度設定
- **タグ機能** - タスクの分類・検索機能
- **並び替え機能** - カンバンボードを想定した並び替え機能

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
- フロントエンド・バックエンド分離（想定は SPA + API 構成）
- FastAPI による OpenAPI 仕様ドキュメントの自動生成

## 🚀 クイックスタート

### 前提条件

- **Python 3.13.4**
- **Docker & Docker Compose**
- **Git**
- **pyenv**

### セットアップ

```bash
# リポジトリをクローン
git clone https://github.com/n-u1/simpletask-backend-fastapi.git
cd simpletask-backend-fastapi

# 環境構築・起動
make setup
make docker-up
make migrate

# 動作確認
# API仕様: http://localhost:8000/docs
# ヘルスチェック: http://localhost:8000/health
```

### 🎉 完了

正常に完了すれば開発環境が準備できます

---

### 環境別の実行方法

**Windows (make コマンドが使えない場合):**

```bash
bash scripts/setup.sh
docker-compose up -d
docker-compose exec simpletask-backend-api alembic upgrade head
```

### トラブルシューティング

**Python バージョンエラー** → `pyenv install 3.13.4 && pyenv local 3.13.4`  
**Docker エラー** → [Docker Desktop](https://docs.docker.com/get-docker/) をインストール  
**ポート 8000 エラー** → `lsof -i :8000` で使用中プロセス確認  
**その他** → `make docker-logs` でログ確認

## 🧪 開発コマンド

```bash
make install     # 依存関係インストール
make docker-up   # Dockerコンテナ起動（make devでも可）
make docker-down # Dockerコンテナ停止
make migrate     # マイグレーション（初回とボリューム削除した際）
make lint        # Lintチェック
make format      # コードフォーマット
make test        # テスト実行
make help        # コマンド一覧
```

## 📚 API

### 認証

```bash
POST /api/v1/auth/register  # ユーザー登録
POST /api/v1/auth/login     # ログイン・JWT取得
```

### タスク

```bash
GET    /api/v1/tasks          # 一覧取得（フィルタ・ソート対応）
POST   /api/v1/tasks          # 作成
PATCH  /api/v1/tasks/reorder  # カンバンボード並び替え
```

詳細: http://localhost:8000/docs

## 🎓 その他

### 実務を意識した取り組み

- レイヤー化による保守性を意識した設計
- setup.sh + Makefile を用いた環境構築や操作の効率化
- Docker による環境統一

### 注意事項

- メジャーバージョン到達前は、一部機能や処理が未実装の場合があります。
