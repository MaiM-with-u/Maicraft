"""
下雨事件实现
"""
from ..base_event import BaseEvent


class RainEvent(BaseEvent):
    """下雨事件"""

    def __init__(self, type: str, gameTick: int, timestamp: float):
        """初始化下雨事件"""
        super().__init__(type, gameTick, timestamp)

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
