from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
import json
import os
from utils.logger import get_logger
from agent.common.basic_class import BlockPosition
from agent.block_cache.block_cache import global_block_cache

logger = get_logger("ContainerCache")


@dataclass
class ContainerInfo:
    """容器信息数据类"""
    position: BlockPosition
    container_type: str
    inventory: Dict[str, int] = None
    # 熔炉专用槽位信息
    furnace_slots: Dict[str, Dict[str, int]] = None
    
    def __post_init__(self):
        if self.inventory is None:
            self.inventory = {}
        if self.furnace_slots is None:
            self.furnace_slots = {}


class GlobalContainerCache:
    """全局容器缓存管理器"""
    
    def __init__(self):
        self.chest_cache: Dict[str, ContainerInfo] = {}
        self.furnace_cache: Dict[str, ContainerInfo] = {}
        self.data_file = "data/container_cache.json"
        self._ensure_data_dir()
        self._load_data()
        logger.info("容器缓存管理器初始化完成")
    
    def _get_position_key(self, position: BlockPosition) -> str:
        """获取位置的唯一键"""
        return f"{position.x}_{position.y}_{position.z}"
    
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
    
    def _save_data(self):
        """保存数据到文件"""
        try:
            data = {
                "chests": {},
                "furnaces": {}
            }
            
            # 转换箱子数据
            for key, container in self.chest_cache.items():
                data["chests"][key] = {
                    "position": container.position.to_dict(),
                    "container_type": container.container_type,
                    "inventory": container.inventory,
                    "furnace_slots": container.furnace_slots
                }
            
            # 转换熔炉数据
            for key, container in self.furnace_cache.items():
                data["furnaces"][key] = {
                    "position": container.position.to_dict(),
                    "container_type": container.container_type,
                    "inventory": container.inventory,
                    "furnace_slots": container.furnace_slots
                }
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"容器缓存数据已保存到: {self.data_file}")
        except Exception as e:
            logger.error(f"保存容器缓存数据失败: {e}")
    
    def _load_data(self):
        """从文件加载数据"""
        try:
            if not os.path.exists(self.data_file):
                logger.info(f"容器缓存数据文件不存在: {self.data_file}")
                return
            
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 加载箱子数据
            for key, container_data in data.get("chests", {}).items():
                position = BlockPosition(**container_data["position"])
                self.chest_cache[key] = ContainerInfo(
                    position=position,
                    container_type=container_data["container_type"],
                    inventory=container_data.get("inventory", {}),
                    furnace_slots=container_data.get("furnace_slots", {})
                )
            
            # 加载熔炉数据
            for key, container_data in data.get("furnaces", {}).items():
                position = BlockPosition(**container_data["position"])
                self.furnace_cache[key] = ContainerInfo(
                    position=position,
                    container_type=container_data["container_type"],
                    inventory=container_data.get("inventory", {}),
                    furnace_slots=container_data.get("furnace_slots", {})
                )
            
            logger.info(f"容器缓存数据已加载: {len(self.chest_cache)} 个箱子, {len(self.furnace_cache)} 个熔炉")
        except Exception as e:
            logger.error(f"加载容器缓存数据失败: {e}")
    
    def verify_container_exists(self, position: BlockPosition, container_type: str) -> bool:
        """验证容器是否实际存在于指定位置"""
        try:
            block = global_block_cache.get_block(position.x, position.y, position.z)
            
            if container_type == "chest":
                return block.block_type == "chest"
            elif container_type == "furnace":
                return block.block_type in ["furnace", "blast_furnace", "smoker"]
            
            return False
        except Exception as e:
            logger.warning(f"验证容器存在性时出错: {e}")
            return False
    
    def remove_container_from_cache(self, position: BlockPosition) -> None:
        """从缓存中移除容器"""
        position_key = self._get_position_key(position)
        
        # 尝试从箱子缓存中移除
        if position_key in self.chest_cache:
            del self.chest_cache[position_key]
            logger.info(f"从缓存中移除箱子: {position.x}, {position.y}, {position.z}")
            self._save_data()
        
        # 尝试从熔炉缓存中移除
        if position_key in self.furnace_cache:
            del self.furnace_cache[position_key]
            logger.info(f"从缓存中移除熔炉: {position.x}, {position.y}, {position.z}")
            self._save_data()
    
    def get_container_info_with_verify(self, position: BlockPosition):
        """获取指定位置的容器信息，并验证容器是否实际存在"""
        container_info = self.get_container_info(position)
        
        if container_info:
            # 验证容器是否实际存在
            if not self.verify_container_exists(position, container_info.container_type):
                logger.warning(f"位置 {position.x}, {position.y}, {position.z} 的{container_info.container_type}已不存在，从缓存中移除")
                self.remove_container_from_cache(position)
                return None
        
        return container_info
    
    def get_nearby_containers_with_verify(self, center_position: BlockPosition, radius: float = 20.0) -> List[ContainerInfo]:
        """获取附近的容器，并验证每个容器是否实际存在"""
        # 获取缓存中的容器列表
        cached_containers = self.get_nearby_containers(center_position, radius)
        
        # 验证每个容器是否实际存在
        valid_containers = []
        removed_positions = []
        
        for container in cached_containers:
            if self.verify_container_exists(container.position, container.container_type):
                valid_containers.append(container)
            else:
                removed_positions.append(container.position)
        
        # 移除不存在的容器
        for position in removed_positions:
            logger.warning(f"位置 {position.x}, {position.y}, {position.z} 的容器已不存在，从缓存中移除")
            self.remove_container_from_cache(position)
        
        return valid_containers
    
    def clean_invalid_containers(self, specific_position: BlockPosition = None) -> int:
        """清理不存在的容器，返回清理的数量"""
        removed_count = 0
        
        if specific_position:
            # 只检查指定位置的容器
            position_key = self._get_position_key(specific_position)
            
            # 检查箱子缓存
            if position_key in self.chest_cache:
                container = self.chest_cache[position_key]
                if not self.verify_container_exists(container.position, "chest"):
                    logger.warning(f"位置 {container.position.x}, {container.position.y}, {container.position.z} 的箱子已不存在，从缓存中移除")
                    del self.chest_cache[position_key]
                    removed_count += 1
            
            # 检查熔炉缓存
            if position_key in self.furnace_cache:
                container = self.furnace_cache[position_key]
                if not self.verify_container_exists(container.position, "furnace"):
                    logger.warning(f"位置 {container.position.x}, {container.position.y}, {container.position.z} 的熔炉已不存在，从缓存中移除")
                    del self.furnace_cache[position_key]
                    removed_count += 1
        else:
            # 检查所有容器（保留原功能以备后用）
            chest_keys_to_remove = []
            for key, container in list(self.chest_cache.items()):
                if not self.verify_container_exists(container.position, "chest"):
                    chest_keys_to_remove.append(key)
            
            furnace_keys_to_remove = []
            for key, container in list(self.furnace_cache.items()):
                if not self.verify_container_exists(container.position, "furnace"):
                    furnace_keys_to_remove.append(key)
            
            # 移除不存在的箱子
            for key in chest_keys_to_remove:
                container = self.chest_cache[key]
                logger.warning(f"位置 {container.position.x}, {container.position.y}, {container.position.z} 的箱子已不存在，从缓存中移除")
                del self.chest_cache[key]
                removed_count += 1
            
            # 移除不存在的熔炉
            for key in furnace_keys_to_remove:
                container = self.furnace_cache[key]
                logger.warning(f"位置 {container.position.x}, {container.position.y}, {container.position.z} 的熔炉已不存在，从缓存中移除")
                del self.furnace_cache[key]
                removed_count += 1
        
        # 如果有移除的容器，保存数据
        if removed_count > 0:
            self._save_data()
            logger.info(f"清理了 {removed_count} 个不存在的容器")
        
        return removed_count
    
    def add_container(self, position: BlockPosition, container_type: str, inventory: Dict[str, int] = None, furnace_slots: Dict[str, Dict[str, int]] = None) -> None:
        """添加容器到缓存"""
        position_key = self._get_position_key(position)
        
        # 选择对应的缓存
        target_cache = self.chest_cache if container_type == "chest" else self.furnace_cache
        
        if position_key in target_cache:
            # 更新现有缓存
            if inventory is not None:
                target_cache[position_key].inventory = dict(inventory)
            if furnace_slots is not None:
                target_cache[position_key].furnace_slots = dict(furnace_slots)
        else:
            # 创建新缓存
            target_cache[position_key] = ContainerInfo(
                position=position,
                container_type=container_type,
                inventory=dict(inventory) if inventory else {},
                furnace_slots=dict(furnace_slots) if furnace_slots else {}
            )
        logger.info(f"添加容器到缓存: {container_type} at ({position.x}, {position.y}, {position.z})")
        
        # 自动保存数据
        self._save_data()
    
    
    def get_nearby_containers(self, center_position: BlockPosition, radius: float = 20.0) -> List[ContainerInfo]:
        """获取附近的容器"""
        nearby_containers = []
        radius_squared = radius * radius
        
        # 合并两个缓存
        all_containers = list(self.chest_cache.values()) + list(self.furnace_cache.values())
        
        for container_info in all_containers:
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
        # 先在箱子缓存中查找，再在熔炉缓存中查找
        return self.chest_cache.get(position_key) or self.furnace_cache.get(position_key)
    
    def update_container_inventory(self, position: BlockPosition, inventory: Dict[str, int], furnace_slots: Dict[str, Dict[str, int]] = None) -> bool:
        """更新容器库存信息"""
        position_key = self._get_position_key(position)
        # 先在箱子缓存中查找，再在熔炉缓存中查找
        if position_key in self.chest_cache:
            self.chest_cache[position_key].inventory = dict(inventory)
            if furnace_slots is not None:
                self.chest_cache[position_key].furnace_slots = dict(furnace_slots)
            # 自动保存数据
            self._save_data()
            return True
        elif position_key in self.furnace_cache:
            self.furnace_cache[position_key].inventory = dict(inventory)
            if furnace_slots is not None:
                self.furnace_cache[position_key].furnace_slots = dict(furnace_slots)
            # 自动保存数据
            self._save_data()
            return True
        return False
    
    def get_cache_info(self) -> str:
        """获取容器缓存信息的字符串表示"""
        if not self.chest_cache and not self.furnace_cache:
            return "附近没有已知的容器"
        
        chests = list(self.chest_cache.values())
        furnaces = list(self.furnace_cache.values())
        
        info_lines = []
        info_lines.append(f"已知的容器: 总共 {len(self.chest_cache) + len(self.furnace_cache)} 个")
        info_lines.append(f"- 箱子: {len(chests)} 个")
        info_lines.append(f"- 熔炉: {len(furnaces)} 个")
        
        if self.chest_cache or self.furnace_cache:
            info_lines.append("\n附近容器详情:")
            all_containers = list(self.chest_cache.values()) + list(self.furnace_cache.values())
            for container in all_containers[:5]:  # 只显示前5个
                pos = container.position
                container_line = f"- {container.container_type} at ({pos.x}, {pos.y}, {pos.z})"
                
                # 添加内容物信息
                if container.container_type == "furnace" and container.furnace_slots:
                    # 熔炉特殊显示格式
                    input_items = []
                    fuel_items = []
                    output_items = []
                    
                    for slot_name, items in container.furnace_slots.items():
                        for item_name, count in items.items():
                            if count > 0:
                                item_str = f"{item_name} x{count}"
                                if slot_name == "input":
                                    input_items.append(item_str)
                                elif slot_name == "fuel":
                                    fuel_items.append(item_str)
                                elif slot_name == "output":
                                    output_items.append(item_str)
                    
                    slot_info = []
                    if input_items:
                        slot_info.append(f"输入: {', '.join(input_items)}")
                    if fuel_items:
                        slot_info.append(f"燃料: {', '.join(fuel_items)}")
                    if output_items:
                        slot_info.append(f"输出: {', '.join(output_items)}")
                    
                    if slot_info:
                        container_line += f" [{'; '.join(slot_info)}]"
                    else:
                        container_line += " [空]"
                else:
                    # 普通容器显示格式
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
            if container.container_type == "furnace" and container.furnace_slots:
                # 熔炉特殊显示格式
                input_items = []
                fuel_items = []
                output_items = []
                
                for slot_name, items in container.furnace_slots.items():
                    for item_name, count in items.items():
                        if count > 0:
                            item_str = f"{item_name} x{count}"
                            if slot_name == "input":
                                input_items.append(item_str)
                            elif slot_name == "fuel":
                                fuel_items.append(item_str)
                            elif slot_name == "output":
                                output_items.append(item_str)
                
                slot_info = []
                if input_items:
                    slot_info.append(f"输入: {', '.join(input_items)}")
                if fuel_items:
                    slot_info.append(f"燃料: {', '.join(fuel_items)}")
                if output_items:
                    slot_info.append(f"输出: {', '.join(output_items)}")
                
                if slot_info:
                    container_line += f" [{'; '.join(slot_info)}]"
                else:
                    container_line += " [空]"
            else:
                # 普通容器显示格式
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