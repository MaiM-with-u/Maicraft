"""
踢出事件实现
"""

from typing import Optional
from typing_extensions import TypedDict
from ..base_event import BaseEvent
from ..event_types import EventType


class KickedEventData(TypedDict):
    reason: Optional[str]  # 踢出原因
    loggedIn: bool  # 如果客户端在成功登录后被踢出，则为 true，如果在登录阶段被踢出，则为 false。


class KickedEvent(BaseEvent[KickedEventData]):
    """bot被踢出事件。当bot被踢出服务器时发出。"""

    EVENT_TYPE = EventType.KICKED.value

    def __init__(
        self, type: str, gameTick: int, timestamp: float, data: KickedEventData = None
    ):
        """初始化踢出事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        reason = f" 原因: {self.data.reason}" if self.data.reason else ""
        return f"你被踢出游戏{reason}"

    def to_dict(self) -> dict:
        result = super().to_dict()
        if self.data.reason:
            result["reason"] = self.data.reason
        result["loggedIn"] = self.data.loggedIn
        return result
