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
    """事件基类，包含所有事件的公共字段"""
    type: str
    timestamp: float
    server_id: str
    player_name: str
    
    # 公共可选字段
    player: Optional[Player] = None
    game_tick: Optional[int] = None
    player_info: Optional[Dict[str, Any]] = None
    position: Optional[Dict[str, float]] = None
    
    def get_category(self) -> str:
        """获取事件分类，子类应该重写此方法"""
        return "unknown"
    
    def to_context_string(self) -> str:
        """为AI提供上下文信息的字符串表示"""
        return f"[{self.type}] {self.player_name}: {self.get_description()}"
    
    def get_description(self) -> str:
        """子类实现具体的描述逻辑"""
        return f"事件类型: {self.type}"
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        result = {
            "type": self.type,
            "timestamp": self.timestamp,
            "server_id": self.server_id,
            "player_name": self.player_name,
            "game_tick": self.game_tick,
        }
        
        # 添加可选字段
        if self.player:
            result["player"] = self.player.__dict__ if hasattr(self.player, '__dict__') else str(self.player)
        if self.position:
            result["position"] = self.position
        if self.player_info:
            result["player_info"] = self.player_info
            
        return result
    
    def __str__(self) -> str:
        """返回事件的字符串表示，保持与原Event类兼容"""
        return self.get_description()


class Event(BaseEvent):
    """Event工厂类，根据事件类型创建对应的子类实例，保持向后兼容"""
    
    def __new__(cls, **kwargs):
        event_type = kwargs.get('type', '')

        # Ensure player_name is set for all events, default to "System"
        if "player_name" not in kwargs or not kwargs["player_name"]:
            kwargs["player_name"] = "System"

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
        """保持现有接口兼容性，从原始数据创建事件对象"""
        event_data = cls._parse_raw_data(event_data_item)
        return cls(**event_data)
    
    @staticmethod
    def _parse_raw_data(event_data_item: Dict[str, Any]) -> dict:
        """解析原始数据，保持现有逻辑"""
        # 基础字段
        event_kwargs = {
            "type": event_data_item.get("type", ""),
            "timestamp": time.time(),
            "server_id": "",
            "player_name": "",
            "game_tick": event_data_item.get("gameTick"),
        }
        
        # 预处理聊天事件的特殊字段
        if event_data_item.get("type") == "chat" and event_data_item.get("chatInfo"):
            chat_info = event_data_item["chatInfo"]
            event_kwargs["chat_text"] = chat_info.get("text", "")
            event_kwargs["player_name"] = chat_info.get("username", "")
        
        # 处理玩家信息
        if event_data_item.get("playerInfo"):
            player_info = event_data_item["playerInfo"]
            event_kwargs["player_info"] = player_info
            event_kwargs["player_name"] = player_info.get("username", "")
            
            # 创建Player对象
            event_kwargs["player"] = Player(
                uuid=player_info.get("uuid", ""),
                username=player_info.get("username", ""),
                display_name=player_info.get("displayName", ""),
                ping=player_info.get("ping", 0),
                gamemode=player_info.get("gamemode", 0)
            )
        elif event_data_item.get("player"):
            player_data = event_data_item["player"]
            event_kwargs["player_name"] = player_data.get("username", "")
            
            # 创建Player对象
            event_kwargs["player"] = Player(
                uuid=player_data.get("uuid", ""),
                username=player_data.get("username", ""),
                display_name=player_data.get("displayName", ""),
                ping=player_data.get("ping", 0),
                gamemode=player_data.get("gamemode", 0)
            )
        
        # 处理playerCollect事件的特殊格式
        elif event_data_item.get("type") == "playerCollect" and event_data_item.get("collector"):
            collector_data = event_data_item["collector"]
            event_kwargs["player_name"] = collector_data.get("username", "")
            
            # 创建Player对象
            event_kwargs["player"] = Player(
                uuid=collector_data.get("uuid", ""),
                username=collector_data.get("username", ""),
                display_name=collector_data.get("displayName", ""),
                ping=0,
                gamemode=0
            )
            
            # 处理收集的物品信息
            collected_items = event_data_item.get("collected", [])
            if collected_items and isinstance(collected_items, list) and len(collected_items) > 0:
                item_info = collected_items[0]
                item_name = item_info.get("displayName", item_info.get("name", "未知物品"))
                item_count = item_info.get("count", 1)
                event_kwargs["item_info"] = {
                    "name": item_name,
                    "count": item_count,
                    "display_text": f"收集了 {item_count} 个 {item_name}"
                }
        
        # 处理位置信息
        if event_data_item.get("position"):
            event_kwargs["position"] = event_data_item["position"]
            
        # 根据事件类型处理特殊字段
        event_type = event_kwargs["type"]
        
        # 为不同事件类型添加相应字段
        if event_type == "chat":
            # 聊天事件已在上面处理
            pass
        elif event_type in ["playerJoined", "playerLeft"]:
            # 玩家加入/离开事件字段
            for field in ["kick_reason"]:
                if field in event_data_item:
                    event_kwargs[field] = event_data_item[field]
        elif event_type == "death":
            # 死亡事件字段 - 使用基础字段
            pass
        elif event_type in ["spawn", "spawnReset"]:
            # 重生相关事件字段 - 使用基础字段
            pass
        elif event_type == "rain":
            # 下雨事件字段 - 使用基础字段
            pass
        elif event_type == "kicked":
            # 踢出事件字段
            for field in ["kick_reason"]:
                if field in event_data_item:
                    event_kwargs[field] = event_data_item[field]
        elif event_type == "health":
            # 健康事件字段
            for field in ["health", "food", "saturation", "experience", "level"]:
                if field in event_data_item:
                    event_kwargs[field] = event_data_item[field]
        elif event_type == "entityHurt":
            # 实体受伤事件字段
            for field in ["entity_name", "damage"]:
                if field in event_data_item:
                    event_kwargs[field] = event_data_item[field]
        elif event_type == "entityDead":
            # 实体死亡事件字段
            for field in ["entity_name"]:
                if field in event_data_item:
                    event_kwargs[field] = event_data_item[field]
        elif event_type == "playerCollect":
            # 玩家收集事件字段 - 已在上面处理
            pass
        else:
            # 其他事件类型，只保留基础字段
            for field in ["weather"]:
                if field in event_data_item:
                    event_kwargs[field] = event_data_item[field]
        
        return event_kwargs
