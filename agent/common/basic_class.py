"""
基础类定义
包含系统中使用的基础数据类和结构
"""
from ast import List
from dataclasses import dataclass
from typing import Optional, Dict, Any, Set
import math
from datetime import datetime


@dataclass
class Player:
    """玩家信息"""
    uuid: str
    username: str
    display_name: str
    ping: int
    gamemode: int


@dataclass
class Position:
    """位置信息"""
    x: float
    y: float
    z: float
    
    def __hash__(self):
        return hash((self.x, self.y, self.z))
    
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y and self.z == other.z
    
    def __sub__(self, other):
        """位置减法操作"""
        if not isinstance(other, Position):
            raise TypeError("只能与 Position 对象进行减法运算")
        return Position(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __truediv__(self, other):
        """位置除法操作（用于除以数字）"""
        if isinstance(other, (int, float)):
            return Position(self.x / other, self.y / other, self.z / other)
        raise TypeError("只能除以数字")
    
    def get_value(self, index):
        """获取指定索引的坐标值"""
        if index == 0:
            return self.x
        elif index == 1:
            return self.y
        elif index == 2:
            return self.z
        else:
            raise IndexError("位置索引必须在 0-2 范围内")
    
    def to_dict(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "z": self.z
        } 


class BlockPosition:
    """方块位置信息（整数坐标，通常用于方块格定位）"""
    x: int
    y: int
    z: int

    def __init__(self, pos: Position|dict|tuple|list = None, x: int = None, y: int = None, z: int = None):
        if pos is not None:
            if isinstance(pos, dict):
                self.x = pos["x"]
                self.y = pos["y"]
                self.z = pos["z"]
            elif isinstance(pos, (tuple, list)) and len(pos) == 3:
                self.x = int(pos[0])
                self.y = int(pos[1])
                self.z = int(pos[2])
            else:
                # 假设是 Position 对象
                self.x = math.floor(pos.x)
                self.y = math.floor(pos.y)
                self.z = math.floor(pos.z)
        elif x is not None and y is not None and z is not None:
            self.x = int(x)
            self.y = int(y)
            self.z = int(z)
        else:
            raise ValueError("必须提供位置参数或 x, y, z 坐标")

    def __hash__(self):
        return hash((self.x, self.y, self.z))
    
    def __eq__(self, other):
        if not isinstance(other, BlockPosition):
            return False
        return self.x == other.x and self.y == other.y and self.z == other.z

    def to_dict(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "z": self.z
        }
        
    def __str__(self) -> str:
        return f"({self.x}, {self.y}, {self.z})"
    
    def distance(self, other) -> float:
        """计算与另一个位置的距离
        
        Args:
            other: Position 或 BlockPosition 对象
            
        Returns:
            float: 欧几里得距离
        """
        if hasattr(other, 'x') and hasattr(other, 'y') and hasattr(other, 'z'):
            dx = self.x - other.x
            dy = self.y - other.y
            dz = self.z - other.z
            return math.sqrt(dx*dx + dy*dy + dz*dz)
        else:
            raise TypeError("other 必须是包含 x, y, z 属性的位置对象")


@dataclass
class Block:
    """方块信息"""
    type: int
    name: str
    position: Position
    
    
TOOL_TAG = ["pickaxe", "axe", "shovel", "hoe", "sword"]
MATERIAL_TAG = [
    (1,"wooden"),
    (2,"golden"),
    (3,"stone"),
    (4,"iron"),
    (5,"diamond"),
    (6,"netherite")
]
class Item:
    """物品信息"""
    def __init__(self, name: str, count: int, slot: int = None, durability: int = 0, max_durability: int = 0):
        self.name = name
        self.count = count
        self.slot = slot
        self.durability = durability
        self.max_durability = max_durability
        
        #对工具的判断
        self.tool_type:str = ""
        self.tool_material:str = ""
        self.tool_material_level:int = 0
        
        for tag in TOOL_TAG:
            if tag in self.name:
                self.tool_type = tag
                break   
        for tag in MATERIAL_TAG:    
            if tag[1] in self.name:
                self.tool_material = tag[1]
                self.tool_material_level = tag[0]
                break
            
    def __str__(self) -> str:
        return f"{self.name} x{self.count}"


@dataclass
class Event:
    """事件信息"""
    type: str
    timestamp: float
    server_id: str
    player_name: str
    player: Optional[Player] = None
    old_position: Optional[Position] = None
    new_position: Optional[Position] = None
    block: Optional[Block] = None
    experience: Optional[int] = None
    level: Optional[int] = None
    health: Optional[int] = None
    food: Optional[int] = None
    saturation: Optional[int] = None
    
    # 新增属性支持更多事件类型
    chat_text: Optional[str] = None  # 聊天消息内容
    kick_reason: Optional[str] = None  # 踢出原因
    entity_name: Optional[str] = None  # 实体名称
    damage: Optional[int] = None  # 伤害值
    entity_position: Optional[Position] = None  # 实体位置
    weather: Optional[str] = None  # 天气信息
    
    # 新增字段支持更多事件类型
    game_tick: Optional[int] = None  # 游戏tick
    player_info: Optional[Dict[str, Any]] = None  # 玩家信息
    position: Optional[Dict[str, float]] = None  # 位置信息
    
    @classmethod
    def from_raw_data(cls, event_data_item: Dict[str, Any]) -> 'Event':
        """从原始事件数据创建Event对象
        
        Args:
            event_data_item: 原始事件数据字典
            
        Returns:
            Event: 创建的事件对象
        """
        import time
        
        # 基础字段
        event_kwargs = {
            "type": event_data_item.get("type", ""),
            "timestamp": time.time(),
            "server_id": "",
            "player_name": "",
            "game_tick": event_data_item.get("gameTick"),
            "weather": event_data_item.get("weather"),
            "health": event_data_item.get("health"),
            "food": event_data_item.get("food"),
            "saturation": event_data_item.get("saturation"),
            "chat_text": ""
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
                event_kwargs["chat_text"] = f"收集了 {item_count} 个 {item_name}"
        
        # 处理位置信息
        if event_data_item.get("position"):
            event_kwargs["position"] = event_data_item["position"]
        
        return cls(**event_kwargs)
    
    def __str__(self) -> str:
        """返回事件的字符串表示"""
        player_name = self.player_name or "未知玩家"
        
        # 根据事件类型返回不同的描述
        if self.type == "chat" and self.chat_text:
            return f"玩家{player_name}说: {self.chat_text}"
        elif self.type == "playerCollect" and self.chat_text:
            return f"玩家{player_name}{self.chat_text}"
        elif self.type == "playerJoin":
            return f"玩家{player_name}进入了游戏"
        elif self.type == "player_quit":
            return f"玩家{player_name}退出了游戏"
        elif self.type == "playerRespawn":
            return f"玩家{player_name}重生了"
        elif self.type == "player_move" and self.old_position and self.new_position:
            return f"玩家{player_name}从{self.old_position}移动到{self.new_position}"
        elif self.type == "block_break" and self.block:
            return f"玩家{player_name}破坏了{self.block.name}方块"
        elif self.type == "block_place" and self.block:
            return f"玩家{player_name}放置了{self.block.name}方块"
        elif self.type == "entity_damage" and self.entity_name and self.damage:
            return f"玩家{player_name}对{self.entity_name}造成了{self.damage}点伤害"
        elif self.type == "player_death":
            return f"玩家{player_name}死亡了"
        elif self.type == "weather_change" and self.weather:
            return f"天气变成了{self.weather}"
        else:
            # 默认格式
            result = f"玩家{player_name}的{self.type}事件"
            return result
    
    def to_dict(self) -> dict:
        """将Event对象转换为字典"""
        result = {
            "type": self.type,
            "timestamp": self.timestamp,
            "server_id": self.server_id,
            "player_name": self.player_name,
            "game_tick": self.game_tick,
            "weather": self.weather,
            "health": self.health,
            "food": self.food,
            "saturation": self.saturation,
            "chat_text": self.chat_text,
            "kick_reason": self.kick_reason,
            "entity_name": self.entity_name,
            "damage": self.damage,
            "experience": self.experience,
            "level": self.level
        }
        
        # 添加可选字段
        if self.player:
            result["player"] = self.player.__dict__ if hasattr(self.player, '__dict__') else str(self.player)
        if self.old_position:
            result["old_position"] = self.old_position.to_dict()
        if self.new_position:
            result["new_position"] = self.new_position.to_dict()
        if self.block:
            result["block"] = self.block.__dict__ if hasattr(self.block, '__dict__') else str(self.block)
        if self.entity_position:
            result["entity_position"] = self.entity_position.to_dict()
        if self.position:
            result["position"] = self.position
        if self.player_info:
            result["player_info"] = self.player_info
            
        return result


@dataclass
class Entity:
    """实体信息"""
    type: str
    name: str
    position: Position
    id: Optional[int] = None
    distance: Optional[float] = None
    health: Optional[int] = None
    max_health: Optional[int] = None
    
    def __str__(self) -> str:
        return f"{self.name} - 坐标: ({self.position.x:.1f}, {self.position.y:.1f}, {self.position.z:.1f})"

class AnimalEntity(Entity):
    """动物实体信息"""
    def __init__(self, type: str, name: str, position: Position, id: Optional[int] = None, distance: Optional[float] = None, health: Optional[int] = None, max_health: Optional[int] = None):
        super().__init__(type, name, position, id, distance, health, max_health)
        
    def __str__(self) -> str:
        return f"动物：{self.name} - 坐标: ({self.position.x:.1f}, {self.position.y:.1f}, {self.position.z:.1f})"

class ItemEntity(Entity):
    """物品实体信息"""
    def __init__(self, type: str, name: str, position: Position, item_name: str, count: Optional[int] = None, id: Optional[int] = None, distance: Optional[float] = None, health: Optional[int] = None, max_health: Optional[int] = None):
        super().__init__(type, name, position, id, distance, health, max_health)
        self.item_name = item_name
        self.count = count
            
    def __str__(self) -> str:
        return f"掉落物：{self.item_name} x {self.count} - 坐标: ({self.position.x:.1f}, {self.position.y:.1f}, {self.position.z:.1f})"
            
class PlayerEntity(Entity):
    """实体信息"""
    def __init__(self, type: str, name: str, position: Position, username: str, id: Optional[int] = None, distance: Optional[float] = None, health: Optional[int] = None, max_health: Optional[int] = None):
        super().__init__(type, name, position, id, distance, health, max_health)
        self.username = username
    
    def __str__(self) -> str:
        return f"玩家：{self.username} - 坐标: ({self.position.x:.1f}, {self.position.y:.1f}, {self.position.z:.1f})"
    
    


class CachedBlock:
    """缓存的方块信息"""
    def __init__(self, block_type: str, position: BlockPosition, can_see: bool, last_seen: datetime, first_seen: datetime, seen_count: int = 1) -> None:
        self.block_type = block_type
        self.position = position
        self.can_see = can_see
        self.last_seen = last_seen
        self.first_seen = first_seen
        self.seen_count = seen_count
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "block_type": self.block_type,
            "position": self.position.to_dict(),
            "can_see": self.can_see,
            "last_seen": self.last_seen.isoformat(),
            "first_seen": self.first_seen.isoformat(),
            "seen_count": self.seen_count
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CachedBlock':
        """从字典创建对象"""
        return cls(
            block_type=data["block_type"],
            position=BlockPosition(data["position"]),
            can_see=data["can_see"] if "can_see" in data else True,
            last_seen=datetime.fromisoformat(data["last_seen"]),
            first_seen=datetime.fromisoformat(data["first_seen"]),
            seen_count=data["seen_count"]
        )
    
    def __hash__(self):
        """使对象可哈希，用于集合操作"""
        return hash((self.position.x, self.position.y, self.position.z))
    
    def __eq__(self, other):
        """比较两个方块是否在同一位置"""
        if not isinstance(other, CachedBlock):
            return False
        return (self.position.x, self.position.y, self.position.z) == (other.position.x, other.position.y, other.position.z)


class PlayerPositionCache:
    """玩家位置和视角信息缓存"""
    def __init__(self, player_name: str, position: Position, yaw: float, pitch: float, timestamp: datetime):
        self.player_name = player_name
        self.position = position
        self.yaw = yaw
        self.pitch = pitch
        self.timestamp = timestamp
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "player_name": self.player_name,
            "position": {
                "x": self.position.x,
                "y": self.position.y,
                "z": self.position.z
            },
            "yaw": self.yaw,
            "pitch": self.pitch,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PlayerPositionCache':
        """从字典创建对象"""
        return cls(
            player_name=data["player_name"],
            position=Position(
                x=data["position"]["x"],
                y=data["position"]["y"],
                z=data["position"]["z"]
            ),
            yaw=data["yaw"],
            pitch=data["pitch"],
            timestamp=datetime.fromisoformat(data["timestamp"])
        )