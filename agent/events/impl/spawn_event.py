"""
重生事件实现
"""
from dataclasses import dataclass
from ..base_event import BaseEvent


@dataclass
class SpawnEvent(BaseEvent):
    """重生事件"""

    def get_description(self) -> str:
        return f"{self.player_name}重生了"
