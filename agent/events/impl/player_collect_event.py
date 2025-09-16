"""
玩家收集事件实现
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from ..base_event import BaseEvent


@dataclass
class PlayerCollectEvent(BaseEvent):
    """玩家收集事件"""
    item_type: Optional[str] = None
    item_count: Optional[int] = None
    item_info: Optional[Dict[str, Any]] = None
    
    def get_description(self) -> str:
        if self.item_info and "display_text" in self.item_info:
            return f"{self.player_name}{self.item_info['display_text']}"
        elif self.item_type:
            count = f" x{self.item_count}" if self.item_count else ""
            return f"{self.player_name}收集了 {self.item_type}{count}"
        return f"{self.player_name}收集了物品"
    
    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            "item_type": self.item_type,
            "item_count": self.item_count,
            "item_info": self.item_info,
        })
        return result
