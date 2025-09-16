"""
玩家移动事件实现
"""
from dataclasses import dataclass
from typing import Optional
from ..base_event import BaseEvent
from ...common.basic_class import Position


@dataclass
class PlayerMoveEvent(BaseEvent):
    """玩家移动事件"""
    old_position: Optional[Position] = None
    new_position: Optional[Position] = None
    
    def get_description(self) -> str:
        if self.old_position and self.new_position:
            return f"{self.player_name}从{self.old_position}移动到{self.new_position}"
        return f"{self.player_name}移动了位置"
    
    def to_dict(self) -> dict:
        result = super().to_dict()
        if self.old_position:
            result["old_position"] = self.old_position.to_dict()
        if self.new_position:
            result["new_position"] = self.new_position.to_dict()
        return result
