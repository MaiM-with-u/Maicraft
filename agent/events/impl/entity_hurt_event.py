"""
实体受伤事件实现
"""
from typing import Optional
from typing_extensions import TypedDict
from ..base_event import BaseEvent
from ..event_types import EventType


class EntityHurtEventData(TypedDict):
    entity_name: Optional[str]
    damage: Optional[int]


class EntityHurtEvent(BaseEvent[EntityHurtEventData]):
    """实体受伤事件"""

    EVENT_TYPE = EventType.ENTITY_HURT.value

    def __init__(self, type: str, gameTick: int, timestamp: float, data: EntityHurtEventData = None):
        """初始化实体受伤事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        if self.data.entity_name and self.data.damage is not None:
            return f"{self.data.entity_name} 受到了 {self.data.damage} 点伤害"
        elif self.data.entity_name:
            return f"{self.data.entity_name} 受到了伤害"
        else:
            return "实体受到了伤害"

    def to_context_string(self) -> str:
        if self.data.entity_name and self.data.damage is not None:
            return f"[entityHurt] {self.data.entity_name} 受到了 {self.data.damage} 点伤害"
        elif self.data.entity_name:
            return f"[entityHurt] {self.data.entity_name} 受到了伤害"
        else:
            return "[entityHurt] 实体受到了伤害"

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            "entity_name": self.data.entity_name,
            "damage": self.data.damage,
        })
        return result
