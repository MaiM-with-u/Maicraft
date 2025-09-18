"""
玩家加入事件实现
"""
from typing import Optional
from ..base_event import BaseEvent
from ..event_types import EventType


class PlayerJoinedEvent(BaseEvent):
    """玩家加入事件"""

    def __init__(self, type: str, gameTick: int, timestamp: float, data: dict = None):
        """初始化玩家加入事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        return f"{self.username}进入了游戏"

    def to_context_string(self) -> str:
        return f"[playerJoined] {self.username} 进入了游戏"

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["player_name"] = self.username
        if self.kick_reason:
            result["kick_reason"] = self.kick_reason
        return result

    @classmethod
    def from_raw_data(cls, event_data_item: dict) -> 'PlayerJoinedEvent':
        """从原始数据创建玩家加入事件"""
        data = event_data_item.get("data", {})
        return cls(
            type=EventType.PLAYER_JOINED.value,
            gameTick=event_data_item.get("gameTick", 0),
            timestamp=event_data_item.get("timestamp", 0),
            data=data
        )
