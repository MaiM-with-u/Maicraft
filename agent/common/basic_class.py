"""
基础类定义
包含系统中使用的基础数据类和结构

Entity使用示例:
    # 从原始entity对象创建
    entity = Entity.from_raw_entity(raw_entity)

    # 手动创建
    entity = Entity(
        id=123,
        uuid="abc-123-def",
        type="player",
        name="Steve",
        username="Steve",
        count=1,
        position=Position(x=10.5, y=64.0, z=-5.2),
        health=20,
        food=18
    )

    # 转换为字典格式
    entity_dict = entity.to_dict()
"""
from dataclasses import dataclass
from typing import Optional
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
    entity: Optional['Entity'] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'Player':
        """从字典创建Player实例"""
        # 处理entity字段，如果是字典则转换为Entity对象
        entity = None
        if data.get('entity'):
            if isinstance(data['entity'], dict):
                entity = Entity.from_raw_entity(data['entity'])
            else:
                entity = data['entity']

        return cls(
            uuid=data.get('uuid', ''),
            username=data.get('username', ''),
            display_name=data.get('display_name', data.get('username', '')),
            ping=data.get('ping', 0),
            gamemode=data.get('gamemode', 0),
            entity=entity
        )


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
    
    def distanceTo(self, other) -> float:
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

    def to_dict(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "z": self.z
        }

    def __str__(self) -> str:
        return f"({self.x:.0f}, {self.y:.0f}, {self.z:.0f})"

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
            self.x = math.floor(x)
            self.y = math.floor(y)
            self.z = math.floor(z)
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
    
    def distanceTo(self, other) -> float:
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
class Entity:
    """实体信息 - 通用实体结构供所有事件复用"""
    id: Optional[int] = None
    uuid: Optional[str] = None
    type: Optional[str] = None
    name: Optional[str] = None
    username: Optional[str] = None
    count: Optional[int] = None
    position: Optional[Position] = None
    health: Optional[int] = None
    food: Optional[int] = None
    distance: Optional[float] = None
    max_health: Optional[int] = None

    @classmethod
    def from_raw_entity(cls, entity) -> 'Entity':
        """从原始entity对象或字典创建Entity实例"""
        if isinstance(entity, dict):
            # 如果是字典，直接使用字典的键值
            return cls(
                id=entity.get('id'),
                uuid=entity.get('uuid'),
                type=entity.get('type'),
                name=entity.get('name'),
                username=entity.get('username'),
                count=entity.get('count'),
                position=cls._parse_position(entity.get('position')),
                health=entity.get('health'),
                food=entity.get('food')
            )
        else:
            # 如果是对象，使用getattr
            return cls(
                id=getattr(entity, 'id', None),
                uuid=getattr(entity, 'uuid', None),
                type=getattr(entity, 'type', None),
                name=getattr(entity, 'name', None),
                username=getattr(entity, 'username', None),
                count=getattr(entity, 'count', None),
                position=cls._parse_position(getattr(entity, 'position', None)),
                health=getattr(entity, 'health', None),
                food=getattr(entity, 'food', None)
            )

    @staticmethod
    def _parse_position(pos) -> Optional[Position]:
        """解析位置信息，支持多种格式"""
        if pos is None:
            return None
        if isinstance(pos, Position):
            return pos
        if hasattr(pos, 'x') and hasattr(pos, 'y') and hasattr(pos, 'z'):
            # 保留两位小数
            return Position(
                x=round(pos.x, 2),
                y=round(pos.y, 2),
                z=round(pos.z, 2)
            )
        if isinstance(pos, dict):
            return Position(
                x=round(pos.get('x', 0), 2),
                y=round(pos.get('y', 0), 2),
                z=round(pos.get('z', 0), 2)
            )
        return None

    def to_dict(self) -> dict:
        """转换为字典格式"""
        result = {}
        if self.id is not None:
            result['id'] = self.id
        if self.uuid is not None:
            result['uuid'] = self.uuid
        if self.type is not None:
            result['type'] = self.type
        if self.name is not None:
            result['name'] = self.name
        if self.username is not None:
            result['username'] = self.username
        if self.count is not None:
            result['count'] = self.count
        if self.position is not None:
            result['position'] = {
                'x': self.position.x,
                'y': self.position.y,
                'z': self.position.z
            }
        if self.health is not None:
            result['health'] = self.health
        if self.food is not None:
            result['food'] = self.food
        if self.distance is not None:
            result['distance'] = self.distance
        if self.max_health is not None:
            result['max_health'] = self.max_health
        return result

    def __str__(self) -> str:
        display_name = self.username or self.name or "未知实体"
        if self.position:
            return f"{display_name} - 坐标: ({self.position.x:.1f}, {self.position.y:.1f}, {self.position.z:.1f})"
        return f"{display_name}"

class AnimalEntity(Entity):
    """动物实体信息"""
    def __init__(self, type: Optional[str] = None, name: Optional[str] = None, position: Optional[Position] = None, id: Optional[int] = None, uuid: Optional[str] = None, username: Optional[str] = None, count: Optional[int] = None, health: Optional[int] = None, food: Optional[int] = None, distance: Optional[float] = None, max_health: Optional[int] = None):
        super().__init__(
            id=id,
            uuid=uuid,
            type=type,
            name=name,
            username=username,
            count=count,
            position=position,
            health=health,
            food=food,
            distance=distance,
            max_health=max_health
        )

    def __str__(self) -> str:
        display_name = self.name or "未知动物"
        if self.position:
            return f"动物：{display_name} - 坐标: ({self.position.x:.1f}, {self.position.y:.1f}, {self.position.z:.1f})"
        return f"动物：{display_name}"

class ItemEntity(Entity):
    """物品实体信息"""
    def __init__(self, type: Optional[str] = None, name: Optional[str] = None, position: Optional[Position] = None, item_name: Optional[str] = None, count: Optional[int] = None, id: Optional[int] = None, uuid: Optional[str] = None, username: Optional[str] = None, health: Optional[int] = None, food: Optional[int] = None, distance: Optional[float] = None, max_health: Optional[int] = None):
        super().__init__(
            id=id,
            uuid=uuid,
            type=type,
            name=name,
            username=username,
            count=count,
            position=position,
            health=health,
            food=food,
            distance=distance,
            max_health=max_health
        )
        self.item_name = item_name

    def __str__(self) -> str:
        display_name = self.item_name or self.name or "未知物品"
        count_str = f" x {self.count}" if self.count else ""
        if self.position:
            return f"掉落物：{display_name}{count_str} - 坐标: ({self.position.x:.1f}, {self.position.y:.1f}, {self.position.z:.1f})"
        return f"掉落物：{display_name}{count_str}"
            
class PlayerEntity(Entity):
    """玩家实体信息"""
    def __init__(self, type: Optional[str] = None, name: Optional[str] = None, position: Optional[Position] = None, username: Optional[str] = None, id: Optional[int] = None, uuid: Optional[str] = None, count: Optional[int] = None, health: Optional[int] = None, food: Optional[int] = None, distance: Optional[float] = None, max_health: Optional[int] = None):
        super().__init__(
            id=id,
            uuid=uuid,
            type=type,
            name=name,
            username=username,
            count=count,
            position=position,
            health=health,
            food=food,
            distance=distance,
            max_health=max_health
        )

    def __str__(self) -> str:
        display_name = self.username or self.name or "未知玩家"
        if self.position:
            return f"玩家：{display_name} - 坐标: ({self.position.x:.1f}, {self.position.y:.1f}, {self.position.z:.1f})"
        return f"玩家：{display_name}"
    
    


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