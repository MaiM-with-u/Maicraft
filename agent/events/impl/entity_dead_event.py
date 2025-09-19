"""
实体死亡事件实现
"""

from typing import Optional
from typing_extensions import TypedDict
from ..base_event import BaseEvent
from ..event_types import EventType
from ...common.basic_class import Entity


class EntityDeadEventData(TypedDict):
    entity: Optional[Entity]


class EntityDeadEvent(BaseEvent[EntityDeadEventData]):
    """实体死亡事件"""

    EVENT_TYPE = EventType.ENTITY_DEAD.value

    def __init__(
        self,
        type: str,
        gameTick: int,
        timestamp: float,
        data: EntityDeadEventData = None,
    ):
        """初始化实体死亡事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        if self.data.entity:
            target = self.data.entity.username or self.data.entity.name or "某实体"
            return f"{target} 死亡了"
        return "某实体 死亡了"

    def to_context_string(self) -> str:
        if self.data.entity:
            target = self.data.entity.username or self.data.entity.name or "某实体"
            return f"[entityDead] {target} 死亡了"
        return "[entityDead] 某实体 死亡了"

    def to_dict(self) -> dict:
        result = super().to_dict()
        if self.data.entity:
            result["entity"] = self.data.entity.to_dict()
        return result
