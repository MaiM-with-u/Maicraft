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
        target = self.entity_name or "某实体"
        return f"{target} 死亡了"

    def to_context_string(self) -> str:
        target = self.entity_name or "某实体"
        return f"[entityDead] {target} 死亡了"

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["entity_name"] = self.entity_name
        return result

    @classmethod
    def from_raw_data(cls, event_data_item: dict) -> 'EntityDeadEvent':
        """从原始数据创建实体死亡事件"""
        return cls(
            type="entityDead",
            gameTick=event_data_item.get("gameTick", 0),
            timestamp=event_data_item.get("timestamp", 0),
            entity_name=event_data_item.get("entity_name")
        )
