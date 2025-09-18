"""
重生事件实现
"""
from typing import Optional, Dict, Any
from typing_extensions import TypedDict
from ..base_event import BaseEvent
from ..event_types import EventType


class SpawnEventData(TypedDict):
    username: str
    position: Optional[Dict[str, Any]]


class SpawnEvent(BaseEvent[SpawnEventData]):
    """重生事件"""

    def __init__(self, type: str, gameTick: int, timestamp: float, data: SpawnEventData = None):
        """初始化重生事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        return f"{self.data.username}重生了"

    def to_context_string(self) -> str:
        return f"[spawn] {self.data.username} 重生了"

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["player_name"] = self.data.username
        return result

    @classmethod
    def from_raw_data(cls, event_data_item: dict) -> 'SpawnEvent':
        """从原始数据创建重生事件"""
        data: SpawnEventData = event_data_item.get("data", {})
        return cls(
            type=EventType.SPAWN.value,
            gameTick=event_data_item.get("gameTick", 0),
            timestamp=event_data_item.get("timestamp", 0),
            data=data
        )
