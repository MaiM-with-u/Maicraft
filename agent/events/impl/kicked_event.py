"""
踢出事件实现
"""
from dataclasses import dataclass
from typing import Optional
from ..base_event import BaseEvent


@dataclass
class KickedEvent(BaseEvent):
    """踢出事件"""
    kick_reason: Optional[str] = None

    def get_description(self) -> str:
        reason = f" 原因: {self.kick_reason}" if self.kick_reason else ""
        return f"{self.player_name}被踢出游戏{reason}"

    def to_dict(self) -> dict:
        result = super().to_dict()
        if self.kick_reason:
            result["kick_reason"] = self.kick_reason
        return result
