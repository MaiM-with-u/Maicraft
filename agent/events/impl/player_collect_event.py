"""
玩家收集事件实现
"""
from typing import Optional, Dict, Any
from ..base_event import BaseEvent
from ..event_types import EventType


class PlayerCollectEvent(BaseEvent):
    """玩家收集事件"""

    def __init__(self, type: str, gameTick: int, timestamp: float, data: dict = None):
        """初始化玩家收集事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        if self.item_info and "display_text" in self.item_info:
            return f"{self.username}{self.item_info['display_text']}"
        elif self.item_type:
            count = f" x{self.item_count}" if self.item_count else ""
            return f"{self.username}收集了 {self.item_type}{count}"
        return f"{self.username}收集了物品"

    def to_context_string(self) -> str:
        if self.item_info and "display_text" in self.item_info:
            return f"[playerCollect] {self.username}{self.item_info['display_text']}"
        elif self.item_type:
            count = f" x{self.item_count}" if self.item_count else ""
            return f"[playerCollect] {self.username} 收集了 {self.item_type}{count}"
        return f"[playerCollect] {self.username} 收集了物品"

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["player_name"] = self.username
        result.update({
            "item_type": self.item_type,
            "item_count": self.item_count,
            "item_info": self.item_info,
        })
        return result

    @classmethod
    def from_raw_data(cls, event_data_item: dict) -> 'PlayerCollectEvent':
        """从原始数据创建玩家收集事件"""
        data = event_data_item.get("data", {})
        return cls(
            type=EventType.PLAYER_COLLECT.value,
            gameTick=event_data_item.get("gameTick", 0),
            timestamp=event_data_item.get("timestamp", 0),
            data=data
        )
