"""
玩家离开事件实现
"""
from typing import Optional
from ..base_event import BaseEvent


class PlayerLeftEvent(BaseEvent):
    """玩家离开事件"""

    def __init__(self, type: str, gameTick: int, timestamp: float, player_name: str = "", kick_reason: Optional[str] = None):
        """初始化玩家离开事件"""
        super().__init__(type, gameTick, timestamp)
        self.player_name = player_name  # 离开的玩家
        self.kick_reason = kick_reason

    def get_description(self) -> str:
        reason = f" 原因: {self.kick_reason}" if self.kick_reason else ""
        return f"{self.player_name}退出了游戏{reason}"

    def to_context_string(self) -> str:
        reason = f" (原因: {self.kick_reason})" if self.kick_reason else ""
        return f"[playerLeft] {self.player_name} 退出了游戏{reason}"

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["player_name"] = self.player_name
        if self.kick_reason:
            result["kick_reason"] = self.kick_reason
        return result

    @classmethod
    def from_raw_data(cls, event_data_item: dict) -> 'PlayerLeftEvent':
        """从原始数据创建玩家离开事件"""
        player_info = event_data_item.get("playerInfo", {})
        return cls(
            type="playerLeft",
            gameTick=event_data_item.get("gameTick", 0),
            timestamp=event_data_item.get("timestamp", 0),
            player_name=player_info.get("username", ""),
            kick_reason=event_data_item.get("kick_reason")
        )
