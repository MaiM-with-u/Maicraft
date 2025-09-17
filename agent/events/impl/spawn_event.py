"""
重生事件实现
"""
from ..base_event import BaseEvent
from ..event_types import EventType


class SpawnEvent(BaseEvent):
    """重生事件"""

    def __init__(self, type: str, gameTick: int, timestamp: float, player_name: str = ""):
        """初始化重生事件"""
        super().__init__(type, gameTick, timestamp)
        self.player_name = player_name  # 重生的玩家

    def get_description(self) -> str:
        return f"{self.player_name}重生了"

    def to_context_string(self) -> str:
        return f"[spawn] {self.player_name} 重生了"

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["player_name"] = self.player_name
        return result

    @classmethod
    def from_raw_data(cls, event_data_item: dict) -> 'SpawnEvent':
        """从原始数据创建重生事件"""
        player_info = event_data_item.get("playerInfo", {})
        return cls(
            type=EventType.SPAWN.value,
            gameTick=event_data_item.get("gameTick", 0),
            timestamp=event_data_item.get("timestamp", 0),
            player_name=player_info.get("username", "")
        )
