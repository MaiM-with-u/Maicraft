"""
玩家离开事件实现
"""
from typing import Optional
from typing_extensions import TypedDict
from ..base_event import BaseEvent
from ..event_types import EventType
from ...common.basic_class import Player


class PlayerLeftEventData(TypedDict):
    player: Player


class PlayerLeftEvent(BaseEvent[PlayerLeftEventData]):
    """玩家离开事件"""

    EVENT_TYPE = EventType.PLAYER_LEFT.value

    def __init__(self, type: str, gameTick: int, timestamp: float, data: PlayerLeftEventData = None):
        """初始化玩家离开事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        username = self.data.player.username
        reason = f" 原因: {self.data.kick_reason}" if self.data.kick_reason else ""
        return f"{username}退出了游戏{reason}"

    def to_context_string(self) -> str:
        username = self.data.player.username
        reason = f" (原因: {self.data.kick_reason})" if self.data.kick_reason else ""
        return f"[playerLeft] {username} 退出了游戏{reason}"

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["player_name"] = self.data.player.username
        result["player"] = self.data.player
        if self.data.kick_reason:
            result["kick_reason"] = self.data.kick_reason
        return result
