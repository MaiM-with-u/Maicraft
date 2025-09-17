"""
事件基类定义
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
import time
from ..common.basic_class import Player, Position, Block
@dataclass
class BaseEvent:
    """事件基类，只包含所有事件都必有的字段"""
    type: str
    gameTick: int
    timestamp: float
    
    def get_category(self) -> str:
        """获取事件分类，子类应该重写此方法"""
        return "unknown"
    
    def to_context_string(self) -> str:
        """为AI提供上下文信息的字符串表示，由子类实现"""
        return f"[{self.type}] {self.get_description()}"
    
    def get_description(self) -> str:
        """子类实现具体的描述逻辑"""
        return f"事件类型: {self.type}"
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "type": self.type,
            "gameTick": self.gameTick,
            "timestamp": self.timestamp,
            "player_name": self.player_name,
        }
    
    def __str__(self) -> str:
        """返回事件的字符串表示，保持与原Event类兼容"""
        return self.get_description()


class Event(BaseEvent):
    """Event工厂类，根据事件类型创建对应的子类实例，保持向后兼容"""
    
    def __new__(cls, **kwargs):
        """使用注册表创建对应的事件实例"""
        from .event_registry import event_registry

        event_type = kwargs.get('type', '')
        event = event_registry.create_event(event_type, **kwargs)

        if event is not None:
            return event
        else:
            # 未知事件类型，使用基类
            return BaseEvent(**kwargs)

    @classmethod
    def from_raw_data(cls, event_data_item: Dict[str, Any]) -> BaseEvent:
        """使用注册表从原始数据创建事件"""
        from .event_registry import event_registry

        event = event_registry.create_event_from_raw_data(event_data_item)

        if event is not None:
            return event
        else:
            # 未知事件类型，使用基类
            event_type = event_data_item.get("type", "")
            return cls(
                type=event_type,
                gameTick=event_data_item.get("gameTick", 0),
                timestamp=event_data_item.get("timestamp", 0)
            )
    
