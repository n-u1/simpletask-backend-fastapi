# SimpleTask テストガイド

SimpleTask アプリケーションのテスト実行方法とテスト構成についてのガイドです。

## 🚀 クイックスタート

```bash
# 全テスト実行
make test

# カバレッジ付きテスト実行
make test-cov
```

## 📝 テスト構成

### Critical テスト（必要最小限）

| カテゴリ         | ファイル                 | 内容                                             |
| ---------------- | ------------------------ | ------------------------------------------------ |
| **認証フロー**   | `test_auth.py`           | ユーザー登録・ログイン・JWT 検証・不正アクセス   |
| **タスク CRUD**  | `test_tasks_crud.py`     | タスクの作成・取得・更新・削除・アクセス制御     |
| **タグ CRUD**    | `test_tags_crud.py`      | タグの作成・取得・更新・削除・アクセス制御       |
| **データ整合性** | `test_data_integrity.py` | リレーション制約・必須フィールド・バリデーション |

### テスト設定構成

```
tests/
├── conftest.py               # 基本フィクスチャとエントリーポイント
├── test_config/
│   ├── app_factory.py        # テストアプリケーション作成
│   ├── database.py           # データベース設定
│   ├── mocks.py              # モック設定（Redis等）
│   └── schema_overrides.py   # テスト用スキーマ置き換え
├── fixtures/
│   ├── auth.py               # 認証関連フィクスチャ
│   ├── entities.py           # エンティティフィクスチャ
│   └── sample_data.py        # サンプルデータフィクスチャ
└── [テストファイル群]
```

### フィクスチャ構成

```python
# 基本フィクスチャ（tests/conftest.py）
db_session      # テスト用データベースセッション
async_client    # 非同期HTTPクライアント

# 認証フィクスチャ（tests/fixtures/auth.py）
auth_headers    # 認証済みヘッダー

# エンティティフィクスチャ（tests/fixtures/entities.py）
test_user       # テスト用ユーザー
test_task       # テスト用タスク
test_tag        # テスト用タグ

# サンプルデータ（tests/fixtures/sample_data.py）
sample_user_data, sample_task_data, sample_tag_data
```

## 🎯 テストコマンド

### Make コマンド

```bash
# 基本テスト
make test              # 全テスト実行
make test-cov          # カバレッジ付きテスト

# カテゴリ別テスト
make test-auth         # 認証テスト
make test-crud         # CRUDテスト
make test-integrity    # データ整合性テスト

# 開発・デバッグ用
make test-failed       # 失敗したテストのみ再実行
make test-debug        # デバッグモード（詳細出力）
```

### 直接 pytest コマンド

```bash
# 基本的なテスト実行
pytest -v                              # 詳細出力
pytest -x                              # 最初の失敗で停止
pytest -s                              # print文の出力表示

# 特定のテスト実行
pytest tests/test_auth.py::TestUserRegistration::test_register_success -v

# その他の便利オプション
pytest --lf                            # 失敗したテストのみ再実行
pytest --cov=app --cov-report=term-missing  # カバレッジ表示
```

## 🔧 テスト環境

### データベース

- **SQLite In-Memory** を使用
- 各テストで独立したデータベース
- 外部キー制約・カスケード削除が有効

### スキーマ

- テスト用の動的スキーマ置き換えを使用（`tests/test_config/schema_overrides.py`）
- 本番の複雑なプロパティを簡素化
- 型安全性を保ちながらテスト環境に最適化

### モック

- Redis 接続のモック化（`tests/test_config/mocks.py`）
- レート制限機能のモック化
- 外部依存関係の除去

## 📋 テスト項目

### ✅ 認証フロー（test_auth.py）

- [x] ユーザー登録（成功・失敗パターン）
- [x] ログイン（成功・失敗パターン）
- [x] JWT 検証・トークン更新
- [x] パスワード変更・ログアウト

### ✅ CRUD 基本動作（test_tasks_crud.py, test_tags_crud.py）

- [x] タスク・タグの作成・取得・更新・削除
- [x] ユーザー固有データのアクセス制御
- [x] 他ユーザーデータへの不正アクセス防止
- [x] タスク-タグ連携機能

### ✅ データ整合性（test_data_integrity.py）

- [x] 必須フィールド・データ型バリデーション
- [x] データベース制約（UNIQUE、外部キー）
- [x] カスケード削除の動作確認
- [x] ビジネスルール制約

## 📈 現在の状況

**Critical 機能のテストが完了：**

- ✅ 認証フロー: 完全テスト済み
- ✅ CRUD 操作: 完全テスト済み
- ✅ データ整合性: 完全テスト済み
- ✅ 主要パスカバレッジ: 確保済み
