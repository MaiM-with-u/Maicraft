"""
踢出事件实现
"""
from dataclasses import dataclass
from typing import Optional
from ..base_event import BaseEvent


@dataclass
class KickedEvent(BaseEvent):
    """踢出事件"""
    player_name: str = ""  # 被踢出的玩家
    kick_reason: Optional[str] = None

    def get_description(self) -> str:
        reason = f" 原因: {self.kick_reason}" if self.kick_reason else ""
        return f"{self.player_name}被踢出游戏{reason}"

    def to_context_string(self) -> str:
        reason = f" (原因: {self.kick_reason})" if self.kick_reason else ""
        return f"[kicked] {self.player_name} 被踢出游戏{reason}"

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["player_name"] = self.player_name
        if self.kick_reason:
            result["kick_reason"] = self.kick_reason
        return result

    @classmethod
    def from_raw_data(cls, event_data_item: dict) -> 'KickedEvent':
        """从原始数据创建踢出事件"""
        player_info = event_data_item.get("playerInfo", {})
        return cls(
            type="kicked",
            gameTick=event_data_item.get("gameTick", 0),
            timestamp=event_data_item.get("timestamp", 0),
            player_name=player_info.get("username", ""),
            kick_reason=event_data_item.get("kick_reason")
        )
