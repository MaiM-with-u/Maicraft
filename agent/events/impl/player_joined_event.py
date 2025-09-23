"""
玩家加入事件实现
"""

from typing_extensions import TypedDict
from ..base_event import BaseEvent
from ..event_types import EventType
from ...common.basic_class import Player


class PlayerJoinedEventData(TypedDict):
    player: Player


class PlayerJoinedEvent(BaseEvent[PlayerJoinedEventData]):
    """玩家加入事件"""

    EVENT_TYPE = EventType.PLAYER_JOINED.value

    def __init__(
        self,
        type: str,
        gameTick: int,
        timestamp: float,
        data: PlayerJoinedEventData = None,
    ):
        """初始化玩家加入事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        username = self.data.player.username
        return f"{username} 进入了游戏"

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["player_name"] = self.data.player.username
        result["player"] = self.data.player
        return result
