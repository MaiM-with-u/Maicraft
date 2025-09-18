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

    def __init__(self, type: str, gameTick: int, timestamp: float, data: ChatEventData = None):
        """初始化聊天事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        return f"{self.data.username}说: {self.data.message}"

    def to_context_string(self) -> str:
        return f"[chat] {self.data.username}: {self.data.message}"

    def to_dict(self) -> dict:
        return super().to_dict()

    @classmethod
    def from_raw_data(cls, event_data_item: dict) -> 'ChatEvent':
        """从原始数据创建聊天事件"""
        data: ChatEventData = event_data_item.get("data", {})
        return cls(
            type=EventType.CHAT.value,
            gameTick=event_data_item.get("gameTick", 0),
            timestamp=event_data_item.get("timestamp", 0),
            data=data
        )
