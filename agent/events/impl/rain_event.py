"""
下雨事件实现
"""
from typing_extensions import TypedDict
from ..base_event import BaseEvent
from ..event_types import EventType


class RainEventData(TypedDict):
    is_raining: bool


class RainEvent(BaseEvent[RainEventData]):
    """下雨事件"""

    EVENT_TYPE = EventType.RAIN.value

    def __init__(self, type: str, gameTick: int, timestamp: float, data: RainEventData = None):
        """初始化下雨事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        return "开始下雨了"

    def to_context_string(self) -> str:
        return "[rain] 开始下雨了"
