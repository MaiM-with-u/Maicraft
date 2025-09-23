"""
重生事件实现
"""

from typing import Optional, Dict, Any
from typing_extensions import TypedDict
from ..base_event import BaseEvent
from ..event_types import EventType
from ...common.basic_class import Player


class SpawnEventData(TypedDict):
    player: Player


class SpawnEvent(BaseEvent[SpawnEventData]):
    """重生事件"""

    EVENT_TYPE = EventType.SPAWN.value

    def __init__(
        self, type: str, gameTick: int, timestamp: float, data: SpawnEventData = None
    ):
        """初始化重生事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        return f"{self.data.player.username}重生了"

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["player_name"] = self.data.player.username
        result["player"] = self.data.player
        return result
