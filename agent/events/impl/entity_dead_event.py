"""
实体死亡事件实现
"""
from dataclasses import dataclass
from typing import Optional
from ..base_event import BaseEvent


@dataclass
class EntityDeadEvent(BaseEvent):
    """实体死亡事件"""
    entity_name: Optional[str] = None

    def get_description(self) -> str:
        target = self.entity_name or self.player_name or "某实体"
        return f"{target} 死亡了"

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["entity_name"] = self.entity_name
        return result
