"""
下雨事件实现
"""
from dataclasses import dataclass
from ..base_event import BaseEvent


@dataclass
class RainEvent(BaseEvent):
    """下雨事件"""

    def get_description(self) -> str:
        return "开始下雨了"
