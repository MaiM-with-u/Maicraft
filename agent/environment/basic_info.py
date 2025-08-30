from dataclasses import dataclass
from typing import Optional, Dict, Any

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