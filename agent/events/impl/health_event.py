"""
健康事件实现
"""
from typing import Optional
from ..base_event import BaseEvent
from ..event_types import EventType


class HealthEvent(BaseEvent):
    """健康事件"""

    def __init__(self, type: str, gameTick: int, timestamp: float, data: dict = None):
        """初始化健康事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        health_info = f"生命值: {self.health}" if self.health is not None else ""
        food_info = f"饱食度: {self.food}" if self.food is not None else ""
        saturation_info = f"饱和度: {self.saturation}" if self.saturation is not None else ""
        info_parts = [info for info in [health_info, food_info, saturation_info] if info]
        status_text = f"状态更新 - {', '.join(info_parts)}" if info_parts else "状态更新"

        return f"{self.username}的{status_text}"

    def to_context_string(self) -> str:
        health_info = f"生命值: {self.health}" if self.health is not None else ""
        food_info = f"饱食度: {self.food}" if self.food is not None else ""
        info_parts = [info for info in [health_info, food_info] if info]
        status_text = f"状态更新 - {', '.join(info_parts)}" if info_parts else "状态更新"
        return f"[health] {self.username}: {status_text}"

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["player_name"] = self.username
        result.update({
            "health": self.health,
            "food": self.food,
            "saturation": self.saturation,
            "experience": self.experience,
            "level": self.level,
        })
        return result

    @classmethod
    def from_raw_data(cls, event_data_item: dict) -> 'HealthEvent':
        """从原始数据创建健康事件"""
        data = event_data_item.get("data", {})
        return cls(
            type=EventType.HEALTH.value,
            gameTick=event_data_item.get("gameTick", 0),
            timestamp=event_data_item.get("timestamp", 0),
            data=data
        )
