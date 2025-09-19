"""
呼吸事件实现
"""

from typing import Optional
from typing_extensions import TypedDict
from ..base_event import BaseEvent
from ..event_types import EventType


class BreathEventData(TypedDict):
    oxygenLevel: Optional[int]
    health: Optional[int]
    food: Optional[int]


class BreathEvent(BaseEvent[BreathEventData]):
    """呼吸事件。当bot的氧气水平发生变化时发出。"""

    EVENT_TYPE = EventType.BREATH.value

    def __init__(
        self, type: str, gameTick: int, timestamp: float, data: BreathEventData = None
    ):
        """初始化呼吸事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        """获取事件的描述信息"""
        oxygen_info = (
            f"氧气水平: {self.data.oxygenLevel}"
            if self.data.oxygenLevel is not None
            else ""
        )
        health_info = (
            f"生命值: {self.data.health}" if self.data.health is not None else ""
        )
        food_info = f"饱食度: {self.data.food}" if self.data.food is not None else ""

        info_parts = [info for info in [oxygen_info, health_info, food_info] if info]
        status_text = (
            f"呼吸状态更新 - {', '.join(info_parts)}" if info_parts else "呼吸状态更新"
        )

        return f"你的{status_text}"

    def to_context_string(self) -> str:
        """转换为上下文字符串，用于AI理解"""
        oxygen_info = (
            f"氧气水平: {self.data.oxygenLevel}"
            if self.data.oxygenLevel is not None
            else ""
        )
        health_info = (
            f"生命值: {self.data.health}" if self.data.health is not None else ""
        )
        food_info = f"饱食度: {self.data.food}" if self.data.food is not None else ""

        info_parts = [info for info in [oxygen_info, health_info, food_info] if info]
        status_text = (
            f"呼吸状态更新 - {', '.join(info_parts)}" if info_parts else "呼吸状态更新"
        )

        return f"[breath] {status_text}"

    def to_dict(self) -> dict:
        """转换为字典格式"""
        result = super().to_dict()
        result.update(
            {
                "oxygenLevel": self.data.oxygenLevel,
                "health": self.data.health,
                "food": self.data.food,
            }
        )
        return result

    def get_oxygen_level(self) -> Optional[int]:
        """获取氧气水平"""
        return self.data.oxygenLevel

    def get_health(self) -> Optional[int]:
        """获取生命值"""
        return self.data.health

    def get_food(self) -> Optional[int]:
        """获取饱食度"""
        return self.data.food

    def is_underwater(self) -> bool:
        """判断是否在水下（氧气水平小于20）"""
        return self.data.oxygenLevel is not None and self.data.oxygenLevel < 20

    def is_drowning(self) -> bool:
        """判断是否正在溺水（氧气水平为0）"""
        return self.data.oxygenLevel == 0
