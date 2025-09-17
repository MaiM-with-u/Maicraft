"""
玩家收集事件实现
"""
from typing import Optional, Dict, Any
from ..base_event import BaseEvent
from ..event_types import EventType


class PlayerCollectEvent(BaseEvent):
    """玩家收集事件"""

    def __init__(self, type: str, gameTick: int, timestamp: float,
                 player_name: str = "", item_type: Optional[str] = None,
                 item_count: Optional[int] = None, item_info: Optional[Dict[str, Any]] = None):
        """初始化玩家收集事件"""
        super().__init__(type, gameTick, timestamp)
        self.player_name = player_name  # 收集物品的玩家
        self.item_type = item_type
        self.item_count = item_count
        self.item_info = item_info

    def get_description(self) -> str:
        if self.item_info and "display_text" in self.item_info:
            return f"{self.player_name}{self.item_info['display_text']}"
        elif self.item_type:
            count = f" x{self.item_count}" if self.item_count else ""
            return f"{self.player_name}收集了 {self.item_type}{count}"
        return f"{self.player_name}收集了物品"

    def to_context_string(self) -> str:
        if self.item_info and "display_text" in self.item_info:
            return f"[playerCollect] {self.player_name}{self.item_info['display_text']}"
        elif self.item_type:
            count = f" x{self.item_count}" if self.item_count else ""
            return f"[playerCollect] {self.player_name} 收集了 {self.item_type}{count}"
        return f"[playerCollect] {self.player_name} 收集了物品"
    
    def to_dict(self) -> dict:
        result = super().to_dict()
        result["player_name"] = self.player_name
        result.update({
            "item_type": self.item_type,
            "item_count": self.item_count,
            "item_info": self.item_info,
        })
        return result

    @classmethod
    def from_raw_data(cls, event_data_item: dict) -> 'PlayerCollectEvent':
        """从原始数据创建玩家收集事件"""
        collector_data = event_data_item.get("collector", {})
        collected_items = event_data_item.get("collected", [])

        item_info = None
        if collected_items and isinstance(collected_items, list) and len(collected_items) > 0:
            item = collected_items[0]
            item_name = item.get("displayName", item.get("name", "未知物品"))
            item_count = item.get("count", 1)
            item_info = {
                "name": item_name,
                "count": item_count,
                "display_text": f"收集了 {item_count} 个 {item_name}"
            }

        return cls(
            type=EventType.PLAYER_COLLECT.value,
            gameTick=event_data_item.get("gameTick", 0),
            timestamp=event_data_item.get("timestamp", 0),
            player_name=collector_data.get("username", ""),
            item_type=item.get("name") if collected_items and len(collected_items) > 0 else None,
            item_count=item.get("count") if collected_items and len(collected_items) > 0 else None,
            item_info=item_info
        )
