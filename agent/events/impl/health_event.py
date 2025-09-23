"""
健康事件实现
"""

from typing import Optional
from typing_extensions import TypedDict
from ..base_event import BaseEvent
from ..event_types import EventType


class HealthEventData(TypedDict):
    health: Optional[int]
    food: Optional[int]
    foodSaturation: Optional[int]


class HealthEvent(BaseEvent[HealthEventData]):
    """健康事件。当bot的生命值、饱食度发生变化时发出。"""

    EVENT_TYPE = EventType.HEALTH.value

    def __init__(
        self, type: str, gameTick: int, timestamp: float, data: HealthEventData = None
    ):
        """初始化健康事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        health_info = (
            f"生命值: {self.data.health}" if self.data.health is not None else ""
        )
        food_info = f"饱食度: {self.data.food}" if self.data.food is not None else ""
        saturation_info = (
            f"饱和度: {self.data.foodSaturation}"
            if self.data.foodSaturation is not None
            else ""
        )
        info_parts = [
            info for info in [health_info, food_info, saturation_info] if info
        ]
        status_text = (
            f"状态更新 - {', '.join(info_parts)}" if info_parts else "状态更新"
        )

        return f"你的{status_text}"

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update(
            {
                "health": self.data.health,
                "food": self.data.food,
                "foodSaturation": self.data.foodSaturation,
            }
        )
        return result
