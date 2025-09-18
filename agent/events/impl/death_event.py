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

    EVENT_TYPE = EventType.DEATH.value

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
