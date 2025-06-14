"""タグDTO

タグデータの転送オブジェクト
"""

from dataclasses import dataclass
from uuid import UUID

from app.dtos.base import BaseDTO


@dataclass(frozen=True)
class TagSummaryDTO:
    """タグ要約DTO（他のエンティティから参照される簡略版）

    TaskDTOなどで使用する軽量なタグ情報
    """

    id: UUID
    name: str
    color: str
    description: str | None = None


@dataclass(frozen=True)
class TagDTO(BaseDTO):
    """タグDTO（完全版）

    タグの完全な情報を含むDTO
    計算プロパティも含む
    """

    user_id: UUID
    name: str
    color: str
    description: str | None
    is_active: bool

    # 集計値（リポジトリ層で計算して設定）
    task_count: int
    active_task_count: int
    completed_task_count: int

    @property
    def color_rgb(self) -> tuple[int, int, int]:
        """カラーコードをRGBタプルに変換"""
        color = self.color.lstrip("#")
        rgb_values = tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))
        return (rgb_values[0], rgb_values[1], rgb_values[2])

    @property
    def is_preset_color(self) -> bool:
        """プリセットカラーかどうか"""
        from app.core.constants import TagConstants

        return self.color in TagConstants.PRESET_COLORS


@dataclass(frozen=True)
class TagListDTO:
    """タグ一覧DTO

    ページネーション情報とタグリストを含む
    """

    tags: list[TagDTO]
    total: int
    page: int
    per_page: int
    total_pages: int
