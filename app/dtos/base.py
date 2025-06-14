"""ベースDTOクラス

すべてのDTOの基底クラスを提供
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class BaseDTO:
    """ベースDTOクラス

    - dataclass(frozen=True): イミュータブルなデータクラス
    - 共通フィールドの定義
    - 型安全性の確保
    """

    id: UUID
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict:
        """辞書形式に変換（デバッグ・ログ出力用）"""
        from dataclasses import asdict

        return asdict(self)
