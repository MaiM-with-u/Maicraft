"""
实体受伤事件实现
"""
from typing import Optional
from typing_extensions import TypedDict
from ..base_event import BaseEvent
from ..event_types import EventType
from ...common.basic_class import Entity


class EntityHurtEventData(TypedDict):
    entity: Optional[Entity]


class EntityHurtEvent(BaseEvent[EntityHurtEventData]):
    """实体受伤事件"""

    EVENT_TYPE = EventType.ENTITY_HURT.value

    def __init__(self, type: str, gameTick: int, timestamp: float, data: EntityHurtEventData = None):
        """初始化实体受伤事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        if self.data.entity:
            target = self.data.entity.username or self.data.entity.name or "实体"
            return f"{target} 受到了伤害，当前生命值为 {self.data.entity.health}"
        else:
            return "实体受到了伤害"

    def to_context_string(self) -> str:
        if self.data.entity:
            target = self.data.entity.username or self.data.entity.name or "实体"
            return f"[entityHurt] {target} 受到了伤害"
        else:
            return "[entityHurt] 实体受到了伤害"

    def to_dict(self) -> dict:
        result = super().to_dict()
        if self.data.entity:
            result["entity"] = self.data.entity.to_dict()
        return result
