"""Alembic環境設定

FastAPI + SQLAlchemy 2.x + PostgreSQL用のマイグレーション設定（同期パターン）
"""

import os
import sys
from logging.config import fileConfig
from pathlib import Path
from urllib.parse import quote_plus

from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection

from alembic import context
from app.models import Base

# プロジェクトのルートディレクトリをPATHに追加
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# モデルのメタデータを設定（autogenerateに必要）
target_metadata = Base.metadata

# データベース設定を環境変数から取得
db_user = os.getenv("DB_USER", "postgres")
db_password = quote_plus(os.getenv("DB_PASSWORD", ""))
db_host = os.getenv("DB_HOST", "localhost")
db_port = os.getenv("DB_PORT", "5432")
db_name = os.getenv("DB_NAME", "simpletask")

# データベースURLを構築
database_url = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

# Alembic設定にURLを設定
config.set_main_option("sqlalchemy.url", database_url)

# 接続情報を表示
print(f"🗄️  データベース接続: {db_host}:{db_port}/{db_name} (user: {db_user})")


def run_migrations_offline() -> None:
    """オフラインモードでマイグレーション実行

    オフラインモードではEngineを作成せず、URLのみでcontextを設定
    実際のDBAPIは不要で、context.execute()がマイグレーションSQLを出力
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # UUID型のサポートを追加
        render_as_batch=False,
        # PostgreSQL固有の設定
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """実際のマイグレーション実行

    Args:
        connection: データベース接続
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # UUID型の比較を有効化
        render_as_batch=False,
        # PostgreSQL固有の設定
        compare_type=True,
        compare_server_default=True,
        # インデックスの比較を有効化
        compare_indexes=True,
        # 制約の比較を有効化
        include_constraints=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """オンラインモードでマイグレーション実行

    実際のEngineを作成してデータベースに接続し、マイグレーションを実行
    """
    connectable = create_engine(
        database_url,
        poolclass=pool.NullPool,
        # デバッグ用（必要に応じてコメントアウト）
        # echo=True,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
