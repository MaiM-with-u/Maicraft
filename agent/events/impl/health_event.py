"""
健康事件实现
"""
from dataclasses import dataclass
from typing import Optional
from ..base_event import BaseEvent


@dataclass
class HealthEvent(BaseEvent):
    """健康事件"""
    health: Optional[int] = None
    food: Optional[int] = None
    saturation: Optional[int] = None
    experience: Optional[int] = None
    level: Optional[int] = None

    def get_description(self) -> str:
        health_info = f"生命值: {self.health}" if self.health is not None else ""
        food_info = f"饱食度: {self.food}" if self.food is not None else ""
        saturation_info = f"饱和度: {self.saturation}" if self.saturation is not None else ""
        info_parts = [info for info in [health_info, food_info, saturation_info] if info]
        status_text = f"状态更新 - {', '.join(info_parts)}" if info_parts else "状态更新"

        # 对于系统事件，如果player_name是System或为空，则不显示玩家名
        if self.player_name and self.player_name != "System":
            return f"{self.player_name}的{status_text}"
        else:
            return status_text

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            "health": self.health,
            "food": self.food,
            "saturation": self.saturation,
            "experience": self.experience,
            "level": self.level,
        })
        return result
