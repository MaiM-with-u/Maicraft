"""
玩家加入事件实现
"""
from dataclasses import dataclass
from ..base_event import BaseEvent


@dataclass
class PlayerJoinEvent(BaseEvent):
    """玩家加入事件"""
    
    def get_description(self) -> str:
        return f"{self.player_name}进入了游戏"
