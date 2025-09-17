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

    def to_context_string(self) -> str:
        return "[rain] 开始下雨了"

    @classmethod
    def from_raw_data(cls, event_data_item: dict) -> 'RainEvent':
        """从原始数据创建下雨事件"""
        return cls(
            type="rain",
            gameTick=event_data_item.get("gameTick", 0),
            timestamp=event_data_item.get("timestamp", 0)
        )
