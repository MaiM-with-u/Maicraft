"""
方块放置事件实现
"""
from dataclasses import dataclass
from typing import Optional
from ..base_event import BaseEvent
from ...common.basic_class import Block


@dataclass
class BlockPlaceEvent(BaseEvent):
    """方块放置事件"""
    block_type: Optional[str] = None
    x: Optional[int] = None
    y: Optional[int] = None
    z: Optional[int] = None
    block: Optional[Block] = None
    
    def get_description(self) -> str:
        block_name = self.block.name if self.block else self.block_type
        pos = f"({self.x}, {self.y}, {self.z})" if all([self.x, self.y, self.z]) else ""
        return f"{self.player_name}放置了 {block_name} {pos}"
    
    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            "block_type": self.block_type,
            "x": self.x,
            "y": self.y,
            "z": self.z,
        })
        if self.block:
            result["block"] = self.block.__dict__ if hasattr(self.block, '__dict__') else str(self.block)
        return result
