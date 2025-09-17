"""
玩家加入事件实现
"""
from typing import Optional
from ..base_event import BaseEvent


class PlayerJoinedEvent(BaseEvent):
    """玩家加入事件"""

    def __init__(self, type: str, gameTick: int, timestamp: float, player_name: str = "", kick_reason: Optional[str] = None):
        """初始化玩家加入事件"""
        super().__init__(type, gameTick, timestamp)
        self.player_name = player_name  # 加入的玩家
        self.kick_reason = kick_reason

    def get_description(self) -> str:
        return f"{self.player_name}进入了游戏"

    def to_context_string(self) -> str:
        return f"[playerJoined] {self.player_name} 进入了游戏"

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["player_name"] = self.player_name
        if self.kick_reason:
            result["kick_reason"] = self.kick_reason
        return result

    @classmethod
    def from_raw_data(cls, event_data_item: dict) -> 'PlayerJoinedEvent':
        """从原始数据创建玩家加入事件"""
        player_info = event_data_item.get("playerInfo", {})
        return cls(
            type="playerJoined",
            gameTick=event_data_item.get("gameTick", 0),
            timestamp=event_data_item.get("timestamp", 0),
            player_name=player_info.get("username", ""),
            kick_reason=event_data_item.get("kick_reason")
        )
