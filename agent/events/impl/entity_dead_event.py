"""
实体死亡事件实现
"""
from typing import Optional
from typing_extensions import TypedDict
from ..base_event import BaseEvent
from ..event_types import EventType


class EntityDeadEventData(TypedDict):
    entity_name: Optional[str]


class EntityDeadEvent(BaseEvent[EntityDeadEventData]):
    """实体死亡事件"""

    EVENT_TYPE = EventType.ENTITY_DEAD.value

    def __init__(self, type: str, gameTick: int, timestamp: float, data: EntityDeadEventData = None):
        """初始化实体死亡事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        target = self.data.entity_name or "某实体"
        return f"{target} 死亡了"

    def to_context_string(self) -> str:
        target = self.data.entity_name or "某实体"
        return f"[entityDead] {target} 死亡了"

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["entity_name"] = self.data.entity_name
        return result
