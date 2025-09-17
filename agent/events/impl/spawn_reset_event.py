"""
重生点重置事件实现
"""
from dataclasses import dataclass
from ..base_event import BaseEvent


@dataclass
class SpawnResetEvent(BaseEvent):
    """重生点重置事件"""

    def get_description(self) -> str:
        return f"{self.player_name}的重生点已重置"
