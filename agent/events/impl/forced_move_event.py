"""
强制移动事件实现
"""

from typing_extensions import TypedDict
from ..base_event import BaseEvent
from ..event_types import EventType
from agent.common.basic_class import Position


class ForcedMoveEventData(TypedDict):
    position: Position  # 位置信息


class ForcedMoveEvent(BaseEvent[ForcedMoveEventData]):
    """强制移动事件。当玩家被强制移动（如传送）时发出。"""

    EVENT_TYPE = EventType.FORCED_MOVE.value

    def __init__(
        self, type: str, gameTick: int, timestamp: float, data: ForcedMoveEventData = None
    ):
        """初始化强制移动事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        if self.data and "position" in self.data:
            pos = self.data.position
            return f"你被强制移动（例如传送指令）到位置 (x={pos.x}, y={pos.y}, z={pos.z})"
        return "你被强制移动"

    def to_context_string(self) -> str:
        if self.data and "position" in self.data:
            pos = self.data.position
            return f"[forcedMove] 你被强制移动（例如传送指令）到位置 (x={pos.x}, y={pos.y}, z={pos.z})"
        return "[forcedMove] 你被强制移动"

    def to_dict(self) -> dict:
        result = super().to_dict()
        if self.data and "position" in self.data:
            result["position"] = self.data.position.to_dict()
        return result
