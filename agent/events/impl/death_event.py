"""
死亡事件实现
"""
from typing_extensions import TypedDict
from ..base_event import BaseEvent
from ..event_types import EventType


class DeathEventData(TypedDict):
    pass


class DeathEvent(BaseEvent[DeathEventData]):
    """bot死亡事件。当bot自身死亡时发出。"""

    EVENT_TYPE = EventType.DEATH.value

    def __init__(self, type: str, gameTick: int, timestamp: float, data: DeathEventData = None):
        """初始化死亡事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        return "你死亡了"

    def to_context_string(self) -> str:
        return "[death] 你死亡了"

    def to_dict(self) -> dict:
        return super().to_dict()
