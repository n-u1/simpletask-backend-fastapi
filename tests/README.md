# SimpleTask テストガイド

SimpleTask アプリケーションのテスト実行方法とテスト構成について説明します。

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

### フィクスチャ（conftest.py）

```python
# 基本フィクスチャ
db_session      # テスト用データベースセッション
async_client    # 非同期HTTPクライアント

# テストデータ
test_user       # テスト用ユーザー
test_task       # テスト用タスク
test_tag        # テスト用タグ
auth_headers    # 認証済みヘッダー

# サンプルデータ
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

- テスト用の簡素化スキーマを使用
- 本番の複雑なプロパティを除外
- Greenlet 問題を回避

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

**開発準備完了：**

- 核となる機能の品質保証が完了
