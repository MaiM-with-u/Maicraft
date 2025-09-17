"""
事件基类定义
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
import time
from ..common.basic_class import Player, Position, Block
# 移除顶部的导入，避免循环导入
# 在工厂方法中进行延迟导入
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
        event_type = kwargs.get('type', '')


        # 每个事件类型对应一个子类，使用延迟导入避免循环依赖
        if event_type == "chat":
            from .impl.chat_event import ChatEvent
            return ChatEvent(**kwargs)
        elif event_type == "playerJoined":
            from .impl.player_joined_event import PlayerJoinedEvent
            return PlayerJoinedEvent(**kwargs)
        elif event_type == "playerLeft":
            from .impl.player_left_event import PlayerLeftEvent
            return PlayerLeftEvent(**kwargs)
        elif event_type == "death":
            from .impl.death_event import DeathEvent
            return DeathEvent(**kwargs)
        elif event_type == "spawn":
            from .impl.spawn_event import SpawnEvent
            return SpawnEvent(**kwargs)
        elif event_type == "rain":
            from .impl.rain_event import RainEvent
            return RainEvent(**kwargs)
        elif event_type == "kicked":
            from .impl.kicked_event import KickedEvent
            return KickedEvent(**kwargs)
        elif event_type == "spawnReset":
            from .impl.spawn_reset_event import SpawnResetEvent
            return SpawnResetEvent(**kwargs)
        elif event_type == "health":
            from .impl.health_event import HealthEvent
            return HealthEvent(**kwargs)
        elif event_type == "entityHurt":
            from .impl.entity_hurt_event import EntityHurtEvent
            return EntityHurtEvent(**kwargs)
        elif event_type == "entityDead":
            from .impl.entity_dead_event import EntityDeadEvent
            return EntityDeadEvent(**kwargs)
        elif event_type == "playerCollect":
            from .impl.player_collect_event import PlayerCollectEvent
            return PlayerCollectEvent(**kwargs)
        else:
            # 未知事件类型，使用基类
            return BaseEvent(**kwargs)

    @classmethod
    def from_raw_data(cls, event_data_item: Dict[str, Any]) -> BaseEvent:
        """从原始数据创建事件，解析逻辑由各子类实现"""
        event_type = event_data_item.get("type", "")

        # 根据事件类型创建相应的事件类
        if event_type == "chat":
            from .impl.chat_event import ChatEvent
            return ChatEvent.from_raw_data(event_data_item)
        elif event_type == "playerJoined":
            from .impl.player_joined_event import PlayerJoinedEvent
            return PlayerJoinedEvent.from_raw_data(event_data_item)
        elif event_type == "playerLeft":
            from .impl.player_left_event import PlayerLeftEvent
            return PlayerLeftEvent.from_raw_data(event_data_item)
        elif event_type == "death":
            from .impl.death_event import DeathEvent
            return DeathEvent.from_raw_data(event_data_item)
        elif event_type == "spawn":
            from .impl.spawn_event import SpawnEvent
            return SpawnEvent.from_raw_data(event_data_item)
        elif event_type == "rain":
            from .impl.rain_event import RainEvent
            return RainEvent.from_raw_data(event_data_item)
        elif event_type == "kicked":
            from .impl.kicked_event import KickedEvent
            return KickedEvent.from_raw_data(event_data_item)
        elif event_type == "spawnReset":
            from .impl.spawn_reset_event import SpawnResetEvent
            return SpawnResetEvent.from_raw_data(event_data_item)
        elif event_type == "health":
            from .impl.health_event import HealthEvent
            return HealthEvent.from_raw_data(event_data_item)
        elif event_type == "entityHurt":
            from .impl.entity_hurt_event import EntityHurtEvent
            return EntityHurtEvent.from_raw_data(event_data_item)
        elif event_type == "entityDead":
            from .impl.entity_dead_event import EntityDeadEvent
            return EntityDeadEvent.from_raw_data(event_data_item)
        elif event_type == "playerCollect":
            from .impl.player_collect_event import PlayerCollectEvent
            return PlayerCollectEvent.from_raw_data(event_data_item)
        else:
            # 未知事件类型，使用基类
            return cls(
                type=event_type,
                gameTick=event_data_item.get("gameTick", 0),
                timestamp=event_data_item.get("timestamp", 0)
            )
    
