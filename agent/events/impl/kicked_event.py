"""
踢出事件实现
"""
from typing import Optional
from ..base_event import BaseEvent
from ..event_types import EventType


class KickedEvent(BaseEvent):
    """踢出事件"""

    def __init__(self, type: str, gameTick: int, timestamp: float,
                 player_name: str = "", kick_reason: Optional[str] = None):
        """初始化踢出事件"""
        super().__init__(type, gameTick, timestamp)
        self.player_name = player_name  # 被踢出的玩家
        self.kick_reason = kick_reason

    def get_description(self) -> str:
        reason = f" 原因: {self.kick_reason}" if self.kick_reason else ""
        return f"{self.player_name}被踢出游戏{reason}"

    def to_context_string(self) -> str:
        reason = f" (原因: {self.kick_reason})" if self.kick_reason else ""
        return f"[kicked] {self.player_name} 被踢出游戏{reason}"

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["player_name"] = self.player_name
        if self.kick_reason:
            result["kick_reason"] = self.kick_reason
        return result

    @classmethod
    def from_raw_data(cls, event_data_item: dict) -> 'KickedEvent':
        """从原始数据创建踢出事件"""
        player_info = event_data_item.get("playerInfo", {})
        return cls(
            type=EventType.KICKED.value,
            gameTick=event_data_item.get("gameTick", 0),
            timestamp=event_data_item.get("timestamp", 0),
            player_name=player_info.get("username", ""),
            kick_reason=event_data_item.get("kick_reason")
        )
