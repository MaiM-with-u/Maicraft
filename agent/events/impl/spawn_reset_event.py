"""
重生点重置事件实现
"""
from typing import Optional
from ..base_event import BaseEvent
from ..event_types import EventType


class SpawnResetEvent(BaseEvent):
    """重生点重置事件"""

    def __init__(self, type: str, gameTick: int, timestamp: float, data: dict = None):
        """初始化重生点重置事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        return f"{self.username}的重生点已重置"

    def to_context_string(self) -> str:
        return f"[spawnReset] {self.username} 的重生点已重置"

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["player_name"] = self.username
        return result

    @classmethod
    def from_raw_data(cls, event_data_item: dict) -> 'SpawnResetEvent':
        """从原始数据创建重生点重置事件"""
        data = event_data_item.get("data", {})
        return cls(
            type=EventType.SPAWN_RESET.value,
            gameTick=event_data_item.get("gameTick", 0),
            timestamp=event_data_item.get("timestamp", 0),
            data=data
        )
