"""
踢出事件实现
"""
from typing import Optional
from typing_extensions import TypedDict
from ..base_event import BaseEvent
from ..event_types import EventType


class KickedEventData(TypedDict):
    username: str
    kick_reason: Optional[str]


class KickedEvent(BaseEvent[KickedEventData]):
    """踢出事件"""

    EVENT_TYPE = EventType.KICKED.value

    def __init__(self, type: str, gameTick: int, timestamp: float, data: KickedEventData = None):
        """初始化踢出事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        reason = f" 原因: {self.data.kick_reason}" if self.data.kick_reason else ""
        return f"{self.data.username}被踢出游戏{reason}"

    def to_context_string(self) -> str:
        reason = f" (原因: {self.data.kick_reason})" if self.data.kick_reason else ""
        return f"[kicked] {self.data.username} 被踢出游戏{reason}"

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["player_name"] = self.data.username
        if self.data.kick_reason:
            result["kick_reason"] = self.data.kick_reason
        return result
