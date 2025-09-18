"""
聊天事件实现
"""
from typing import Optional, Any
from typing_extensions import TypedDict
from ..base_event import BaseEvent
from ..event_types import EventType


class ChatEventData(TypedDict):
    username: str
    message: str
    translate: Optional[str]
    jsonMsg: Optional[Any]
    matches: Optional[Any]


class ChatEvent(BaseEvent[ChatEventData]):
    """聊天事件"""

    EVENT_TYPE = EventType.CHAT.value

    def __init__(self, type: str, gameTick: int, timestamp: float, data: ChatEventData = None):
        """初始化聊天事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        return f"{self.data.username}说: {self.data.message}"

    def to_context_string(self) -> str:
        return f"[chat] {self.data.username}: {self.data.message}"

    def to_dict(self) -> dict:
        return super().to_dict()
