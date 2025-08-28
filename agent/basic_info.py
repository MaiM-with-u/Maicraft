from dataclasses import dataclass
from typing import Optional

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

    def __init__(self, pos: Position|dict):
        if isinstance(pos, dict):
            self.x = pos["x"]
            self.y = pos["y"]
            self.z = pos["z"]
        else:
            if pos.x >0:
                self.x = int(pos.x)
            else:
                self.x = int(pos.x) -1 
                
            if pos.y >0:
                self.y = int(pos.y)
            else:
                self.y = int(pos.y) -1
                
            if pos.z >0:
                self.z = int(pos.z)
            else:
                self.z = int(pos.z) -1

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


@dataclass
class Block:
    """方块信息"""
    type: int
    name: str
    position: Position


@dataclass
class Event:
    """事件信息"""
    type: str
    timestamp: int
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