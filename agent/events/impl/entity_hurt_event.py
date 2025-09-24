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
    source: Optional[Entity] # 伤害来源，但是mineflayer那边该事件的监听存在些问题，不知为何只要接收伤害来源参数，就会导致频繁掉线，所以暂时先不使用该参数


class EntityHurtEvent(BaseEvent[EntityHurtEventData]):
    """实体受伤事件"""

    EVENT_TYPE = EventType.ENTITY_HURT.value

    def __init__(
        self,
        type: str,
        gameTick: int,
        timestamp: float,
        data: EntityHurtEventData = None,
    ):
        """初始化实体受伤事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        if self.data.entity:
            target = self.data.entity.username or self.data.entity.name or "实体"
            source_desc = ""
            if hasattr(self.data, 'source') and self.data.source:
                source = self.data.source.username or self.data.source.name or "实体"
                source_desc = f"，伤害来源：{source}"

            return f"{target} 受到了伤害{source_desc}，当前生命值为 {self.data.entity.health}"
        else:
            return "实体受到了伤害"


    def to_dict(self) -> dict:
        result = super().to_dict()
        if self.data.entity:
            result["entity"] = self.data.entity.to_dict()
        if hasattr(self.data, 'source') and self.data.source:
            result["source"] = self.data.source.to_dict()
        return result
