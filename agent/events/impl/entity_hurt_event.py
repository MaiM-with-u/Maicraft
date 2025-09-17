"""
实体受伤事件实现
"""
from typing import Optional
from ..base_event import BaseEvent


class EntityHurtEvent(BaseEvent):
    """实体受伤事件"""

    def __init__(self, type: str, gameTick: int, timestamp: float,
                 entity_name: Optional[str] = None, damage: Optional[int] = None):
        """初始化实体受伤事件"""
        super().__init__(type, gameTick, timestamp)
        self.entity_name = entity_name
        self.damage = damage

    def get_description(self) -> str:
        if self.entity_name and self.damage is not None:
            return f"{self.entity_name} 受到了 {self.damage} 点伤害"
        elif self.entity_name:
            return f"{self.entity_name} 受到了伤害"
        else:
            return "实体受到了伤害"

    def to_context_string(self) -> str:
        if self.entity_name and self.damage is not None:
            return f"[entityHurt] {self.entity_name} 受到了 {self.damage} 点伤害"
        elif self.entity_name:
            return f"[entityHurt] {self.entity_name} 受到了伤害"
        else:
            return "[entityHurt] 实体受到了伤害"

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            "entity_name": self.entity_name,
            "damage": self.damage,
        })
        return result

    @classmethod
    def from_raw_data(cls, event_data_item: dict) -> 'EntityHurtEvent':
        """从原始数据创建实体受伤事件"""
        return cls(
            type="entityHurt",
            gameTick=event_data_item.get("gameTick", 0),
            timestamp=event_data_item.get("timestamp", 0),
            entity_name=event_data_item.get("entity_name"),
            damage=event_data_item.get("damage")
        )
