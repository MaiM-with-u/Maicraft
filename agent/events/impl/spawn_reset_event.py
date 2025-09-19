"""
重生点重置事件实现
"""

from typing import Optional
from typing_extensions import TypedDict
from ..base_event import BaseEvent
from ..event_types import EventType
from ...common.basic_class import Position


class SpawnResetEventData(TypedDict):
    newSpawnPoint: Position


class SpawnResetEvent(BaseEvent[SpawnResetEventData]):
    """重生点重置事件"""

    EVENT_TYPE = EventType.SPAWN_RESET.value

    def __init__(
        self,
        type: str,
        gameTick: int,
        timestamp: float,
        data: SpawnResetEventData = None,
    ):
        """初始化重生点重置事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        return f"你的重生点已重置为{self.data.newSpawnPoint}"

    def to_context_string(self) -> str:
        return f"[spawnReset] 你的重生点已重置为{self.data.newSpawnPoint}"

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["newSpawnPoint"] = self.data.newSpawnPoint
        return result
