"""
聊天事件实现
"""
from typing import Optional, Any
from typing_extensions import TypedDict
from ..base_event import BaseEvent
from ..event_types import EventType


class ChatEventData(TypedDict):
    username: str # 发送消息的玩家名称
    message: str # 发送的消息内容
    translate: Optional[str] # 聊天消息类型。大多数 bukkit 聊天消息为 null
    jsonMsg: Optional[Any] # 服务器未修改的 JSON 消息
    matches: Optional[Any] # 正则表达式返回的匹配数组。可能为 null


class ChatEvent(BaseEvent[ChatEventData]):
    """聊天事件。仅当玩家公开聊天时才会发出。"""

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
