"""
事件基类定义
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
import time
from ..common.basic_class import Player, Position, Block


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

        # 修正历史遗留的蛇形命名
        event_type = cls._normalize_event_type(event_type)
        kwargs['type'] = event_type

        # Ensure player_name is set for all events, default to "System"
        if "player_name" not in kwargs or not kwargs["player_name"]:
            kwargs["player_name"] = "System"

        # 每个事件类型对应一个子类
        if event_type == "chat":
            from .impl.chat_event import ChatEvent
            return ChatEvent(**kwargs)
        elif event_type == "playerJoin":
            from .impl.player_join_event import PlayerJoinEvent
            return PlayerJoinEvent(**kwargs)
        elif event_type == "playerLeave":
            from .impl.player_leave_event import PlayerLeaveEvent
            return PlayerLeaveEvent(**kwargs)
        elif event_type == "playerMove":
            from .impl.player_move_event import PlayerMoveEvent
            return PlayerMoveEvent(**kwargs)
        elif event_type == "playerRespawn":
            from .impl.player_respawn_event import PlayerRespawnEvent
            return PlayerRespawnEvent(**kwargs)
        elif event_type == "blockBreak":
            from .impl.block_break_event import BlockBreakEvent
            return BlockBreakEvent(**kwargs)
        elif event_type == "blockPlace":
            from .impl.block_place_event import BlockPlaceEvent
            return BlockPlaceEvent(**kwargs)
        elif event_type == "itemPickup":
            from .impl.item_pickup_event import ItemPickupEvent
            return ItemPickupEvent(**kwargs)
        elif event_type == "itemDrop":
            from .impl.item_drop_event import ItemDropEvent
            return ItemDropEvent(**kwargs)
        elif event_type == "playerCollect":
            from .impl.player_collect_event import PlayerCollectEvent
            return PlayerCollectEvent(**kwargs)
        elif event_type == "healthUpdate":
            from .impl.health_update_event import HealthUpdateEvent
            return HealthUpdateEvent(**kwargs)
        else:
            # 未知事件类型，使用基类
            return BaseEvent(**kwargs)
    
    @staticmethod
    def _normalize_event_type(event_type: str) -> str:
        """修正历史遗留的蛇形命名为正确的驼峰命名"""
        mapping = {
            "player_quit": "playerQuit",
            "player_move": "playerMove", 
            "block_break": "blockBreak",
            "block_place": "blockPlace",
            # 无效事件类型过滤
            "entity_damage": "unknown",
            "entity_death": "unknown",
            "player_death": "unknown",
        }
        return mapping.get(event_type, event_type)

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
        elif event_type in ["playerJoin", "playerLeave", "playerMove", "playerRespawn"]:
            # 玩家事件字段
            for field in ["kick_reason", "old_position", "new_position"]:
                if field in event_data_item:
                    if field.endswith("position") and isinstance(event_data_item[field], dict):
                        event_kwargs[field] = Position(**event_data_item[field])
                    else:
                        event_kwargs[field] = event_data_item[field]
        elif event_type in ["blockBreak", "blockPlace"]:
            # 方块事件字段
            for field in ["block_type", "x", "y", "z"]:
                if field in event_data_item:
                    event_kwargs[field] = event_data_item[field]
            if "block" in event_data_item and isinstance(event_data_item["block"], dict):
                event_kwargs["block"] = Block(**event_data_item["block"])
        elif event_type in ["itemPickup", "itemDrop", "playerCollect"]:
            # 物品事件字段 - 已在上面处理playerCollect
            for field in ["item_type", "item_count", "item_info"]:
                if field in event_data_item:
                    event_kwargs[field] = event_data_item[field]
        elif event_type == "healthUpdate":
            # 健康更新事件字段
            for field in ["health", "food", "saturation", "experience", "level"]:
                if field in event_data_item:
                    event_kwargs[field] = event_data_item[field]
        else:
            # 其他事件类型，只保留基础字段
            for field in ["weather"]:
                if field in event_data_item:
                    event_kwargs[field] = event_data_item[field]
        
        return event_kwargs
