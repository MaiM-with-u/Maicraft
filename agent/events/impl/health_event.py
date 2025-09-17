"""
健康事件实现
"""
from typing import Optional
from ..base_event import BaseEvent


class HealthEvent(BaseEvent):
    """健康事件"""

    def __init__(self, type: str, gameTick: int, timestamp: float,
                 player_name: str = "", health: Optional[int] = None,
                 food: Optional[int] = None, saturation: Optional[int] = None,
                 experience: Optional[int] = None, level: Optional[int] = None):
        """初始化健康事件"""
        super().__init__(type, gameTick, timestamp)
        self.player_name = player_name  # 状态更新的玩家
        self.health = health
        self.food = food
        self.saturation = saturation
        self.experience = experience
        self.level = level

    def get_description(self) -> str:
        health_info = f"生命值: {self.health}" if self.health is not None else ""
        food_info = f"饱食度: {self.food}" if self.food is not None else ""
        saturation_info = f"饱和度: {self.saturation}" if self.saturation is not None else ""
        info_parts = [info for info in [health_info, food_info, saturation_info] if info]
        status_text = f"状态更新 - {', '.join(info_parts)}" if info_parts else "状态更新"

        return f"{self.player_name}的{status_text}"

    def to_context_string(self) -> str:
        health_info = f"生命值: {self.health}" if self.health is not None else ""
        food_info = f"饱食度: {self.food}" if self.food is not None else ""
        info_parts = [info for info in [health_info, food_info] if info]
        status_text = f"状态更新 - {', '.join(info_parts)}" if info_parts else "状态更新"
        return f"[health] {self.player_name}: {status_text}"

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["player_name"] = self.player_name
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
        player_info = event_data_item.get("playerInfo", {})
        return cls(
            type="health",
            gameTick=event_data_item.get("gameTick", 0),
            timestamp=event_data_item.get("timestamp", 0),
            player_name=player_info.get("username", ""),
            health=event_data_item.get("health"),
            food=event_data_item.get("food"),
            saturation=event_data_item.get("saturation"),
            experience=event_data_item.get("experience"),
            level=event_data_item.get("level")
        )
