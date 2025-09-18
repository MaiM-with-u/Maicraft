"""
死亡事件实现
"""
from typing_extensions import TypedDict
from ..base_event import BaseEvent
from ..event_types import EventType


class DeathEventData(TypedDict):
    username: str


class DeathEvent(BaseEvent[DeathEventData]):
    """死亡事件"""

    def __init__(self, type: str, gameTick: int, timestamp: float, data: DeathEventData = None):
        """初始化死亡事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        return f"{self.data.username} 死亡了"

    def to_context_string(self) -> str:
        return f"[death] {self.data.username} 死亡了"

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["player_name"] = self.data.username
        return result

    @classmethod
    def from_raw_data(cls, event_data_item: dict) -> 'DeathEvent':
        """从原始数据创建死亡事件"""
        data: DeathEventData = event_data_item.get("data", {})
        return cls(
            type=EventType.DEATH.value,
            gameTick=event_data_item.get("gameTick", 0),
            timestamp=event_data_item.get("timestamp", 0),
            data=data
        )
