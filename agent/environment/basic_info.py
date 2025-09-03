from dataclasses import dataclass
from typing import Optional, Dict, Any
import math

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
    
    def to_dict(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "z": self.z
        } 
        
@dataclass
class BlockPosition:
    """方块位置信息（整数坐标，通常用于方块格定位）"""
    x: int
    y: int
    z: int

    def __init__(self, pos: Position|dict|tuple|list = None, x: int = None, y: int = None, z: int = None):
        # 检查是否直接传入了三个位置参数
        if pos is not None and x is not None and y is not None and z is None:
            # 如果 pos 是数字，x 是数字，y 是数字，z 是 None，说明是直接传入三个参数
            if isinstance(pos, (int, float)) and isinstance(x, (int, float)) and isinstance(y, (int, float)):
                self.x = int(pos)
                self.y = int(x)
                self.z = int(y)
                return
        
        if pos is not None:
            if isinstance(pos, dict):
                self.x = pos["x"]
                self.y = pos["y"]
                self.z = pos["z"]
            elif isinstance(pos, (tuple, list)) and len(pos) == 3:
                self.x = int(pos[0])
                self.y = int(pos[1])
                self.z = int(pos[2])
            elif isinstance(pos, Position):
                # 假设是 Position 对象
                self.x = math.floor(pos.x)
                self.y = math.floor(pos.y)
                self.z = math.floor(pos.z)
            else:
                raise ValueError("必须提供Position对象或dict,tuple,list")
        elif x is not None and y is not None and z is not None:
            self.x = math.floor(x)
            self.y = math.floor(y)
            self.z = math.floor(z)
        else:
            raise ValueError("必须提供Position对象或dict,tuple,list或 x, y, z 坐标")

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
        
    def __str__(self) -> str:
        return f"x={self.x}, y={self.y}, z={self.z}"


@dataclass
class EventBlock:
    """方块信息"""
    type: int
    name: str
    position: BlockPosition
    
    

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
    def __init__(self, name: str, count: int, slot: int, durability: int = 0, max_durability: int = 0):
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
    block: Optional[EventBlock] = None
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
    id: int
    type: str
    name: str
    position: Position
    distance: Optional[float] = None
    health: Optional[int] = None
    max_health: Optional[int] = None