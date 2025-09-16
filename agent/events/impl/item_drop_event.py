"""
物品丢弃事件实现
"""
from dataclasses import dataclass
from typing import Optional
from ..base_event import BaseEvent


@dataclass
class ItemDropEvent(BaseEvent):
    """物品丢弃事件"""
    item_type: Optional[str] = None
    item_count: Optional[int] = None
    
    def get_description(self) -> str:
        if self.item_type:
            count = f" x{self.item_count}" if self.item_count else ""
            return f"{self.player_name}丢弃了 {self.item_type}{count}"
        return f"{self.player_name}丢弃了物品"
    
    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            "item_type": self.item_type,
            "item_count": self.item_count,
        })
        return result
