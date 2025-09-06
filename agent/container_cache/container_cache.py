from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass
from utils.logger import get_logger
from agent.environment.basic_info import BlockPosition

logger = get_logger("ContainerCache")


@dataclass
class ContainerInfo:
    """容器信息数据类"""
    position: BlockPosition
    container_type: str
    last_accessed: datetime
    lifetime: int
    inventory: Dict[str, int] = None
    
    def __post_init__(self):
        if self.inventory is None:
            self.inventory = {}


class GlobalContainerCache:
    """全局容器缓存管理器"""
    
    def __init__(self, cache_lifetime: int = 10):
        self.container_cache: Dict[str, ContainerInfo] = {}
        self.cache_lifetime = cache_lifetime
        logger.info("容器缓存管理器初始化完成")
    
    def _get_position_key(self, position: BlockPosition) -> str:
        """获取位置的唯一键"""
        return f"{position.x}_{position.y}_{position.z}"
    
    def add_container(self, position: BlockPosition, container_type: str, inventory: Dict[str, int] = None) -> None:
        """添加容器到缓存"""
        position_key = self._get_position_key(position)
        
        if position_key in self.container_cache:
            # 更新现有缓存
            self.container_cache[position_key].last_accessed = datetime.now()
            self.container_cache[position_key].lifetime = self.cache_lifetime
            if inventory is not None:
                self.container_cache[position_key].inventory = dict(inventory)
        else:
            # 创建新缓存
            self.container_cache[position_key] = ContainerInfo(
                position=position,
                container_type=container_type,
                last_accessed=datetime.now(),
                lifetime=self.cache_lifetime,
                inventory=dict(inventory) if inventory else {}
            )
        logger.info(f"添加容器到缓存: {container_type} at ({position.x}, {position.y}, {position.z})")
    
    def update_cache_lifetime(self) -> None:
        """更新容器缓存生命周期"""
        expired_keys = []
        
        for position_key, container_info in self.container_cache.items():
            container_info.lifetime -= 1
            if container_info.lifetime <= 0:
                expired_keys.append(position_key)
        
        # 移除过期缓存
        for position_key in expired_keys:
            del self.container_cache[position_key]
            logger.info(f"移除过期容器缓存: {position_key}")
    
    def get_nearby_containers(self, center_position: BlockPosition, radius: float = 20.0) -> List[ContainerInfo]:
        """获取附近的容器"""
        nearby_containers = []
        radius_squared = radius * radius
        
        for container_info in self.container_cache.values():
            pos = container_info.position
            dx = pos.x - center_position.x
            dy = pos.y - center_position.y
            dz = pos.z - center_position.z
            distance_squared = dx * dx + dy * dy + dz * dz
            
            if distance_squared <= radius_squared:
                nearby_containers.append(container_info)
        
        # 按距离排序
        nearby_containers.sort(key=lambda c: (
            (c.position.x - center_position.x) ** 2 +
            (c.position.y - center_position.y) ** 2 +
            (c.position.z - center_position.z) ** 2
        ))
        
        return nearby_containers
    
    def get_container_info(self, position: BlockPosition) -> ContainerInfo:
        """获取指定位置的容器信息"""
        position_key = self._get_position_key(position)
        return self.container_cache.get(position_key)
    
    def update_container_inventory(self, position: BlockPosition, inventory: Dict[str, int]) -> bool:
        """更新容器库存信息"""
        position_key = self._get_position_key(position)
        if position_key in self.container_cache:
            self.container_cache[position_key].inventory = dict(inventory)
            self.container_cache[position_key].last_accessed = datetime.now()
            return True
        return False
    
    def get_cache_info(self) -> str:
        """获取容器缓存信息的字符串表示"""
        if not self.container_cache:
            return "附近没有已知的容器"
        
        chests = [c for c in self.container_cache.values() if c.container_type == "chest"]
        furnaces = [c for c in self.container_cache.values() if c.container_type == "furnace"]
        
        info_lines = []
        info_lines.append(f"已知的容器: 总共 {len(self.container_cache)} 个")
        info_lines.append(f"- 箱子: {len(chests)} 个")
        info_lines.append(f"- 熔炉: {len(furnaces)} 个")
        
        if self.container_cache:
            info_lines.append("\n附近容器详情:")
            for container in list(self.container_cache.values())[:5]:  # 只显示前5个
                pos = container.position
                container_line = f"- {container.container_type} at ({pos.x}, {pos.y}, {pos.z})"
                
                # 添加内容物信息
                if container.inventory:
                    items = []
                    for item_name, count in container.inventory.items():
                        if count > 0:
                            items.append(f"{item_name} x{count}")
                    if items:
                        container_line += f" [{', '.join(items)}]"
                    else:
                        container_line += " [空]"
                else:
                    container_line += " [空]"
                
                info_lines.append(container_line)
        
        return "\n".join(info_lines)
    
    def get_nearby_containers_info(self, center_position: BlockPosition, max_count: int = 3) -> str:
        """获取附近容器信息的字符串表示"""
        nearby_containers = self.get_nearby_containers(center_position)
        if not nearby_containers:
            return ""
        
        info_lines = []
        
        for container in nearby_containers[:max_count]:
            pos = container.position
            container_type = "箱子" if container.container_type == "chest" else "熔炉"
            
            # 构建容器信息行
            container_line = f"- {container_type} at ({pos.x}, {pos.y}, {pos.z})"
            
            # 添加内容物信息
            if container.inventory:
                items = []
                for item_name, count in container.inventory.items():
                    if count > 0:
                        items.append(f"{item_name} x{count}")
                if items:
                    container_line += f" [{', '.join(items)}]"
                else:
                    container_line += " [空]"
            else:
                container_line += " [空]"
            
            info_lines.append(container_line)
        
        return "\n".join(info_lines)
    



# 创建全局实例
global_container_cache = GlobalContainerCache()