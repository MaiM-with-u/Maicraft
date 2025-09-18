"""
玩家收集事件实现
"""
from typing import Optional, Dict, Any
from typing_extensions import TypedDict
from ..base_event import BaseEvent
from ..event_types import EventType


class PlayerCollectEventData(TypedDict):
    username: str
    item_type: Optional[str]
    item_count: Optional[int]
    item_info: Optional[Dict[str, Any]]


class PlayerCollectEvent(BaseEvent[PlayerCollectEventData]):
    """玩家收集事件"""

    EVENT_TYPE = EventType.PLAYER_COLLECT.value

    def __init__(self, type: str, gameTick: int, timestamp: float, data: PlayerCollectEventData = None):
        """初始化玩家收集事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        if self.data.item_info and "display_text" in self.data.item_info:
            return f"{self.data.username}{self.data.item_info['display_text']}"
        elif self.data.item_type:
            count = f" x{self.data.item_count}" if self.data.item_count else ""
            return f"{self.data.username}收集了 {self.data.item_type}{count}"
        return f"{self.data.username}收集了物品"

    def to_context_string(self) -> str:
        if self.data.item_info and "display_text" in self.data.item_info:
            return f"[playerCollect] {self.data.username}{self.data.item_info['display_text']}"
        elif self.data.item_type:
            count = f" x{self.data.item_count}" if self.data.item_count else ""
            return f"[playerCollect] {self.data.username} 收集了 {self.data.item_type}{count}"
        return f"[playerCollect] {self.data.username} 收集了物品"

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["player_name"] = self.data.username
        result.update({
            "item_type": self.data.item_type,
            "item_count": self.data.item_count,
            "item_info": self.data.item_info,
        })
        return result
