"""
死亡事件实现
"""
from dataclasses import dataclass
from ..base_event import BaseEvent


@dataclass
class DeathEvent(BaseEvent):
    """死亡事件"""

    def get_description(self) -> str:
        target = self.player_name or "某玩家"
        return f"{target} 死亡了"
