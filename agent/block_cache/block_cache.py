"""
方块缓存系统
用于缓存和管理所有获取过的方块信息
支持位置更新、查询和统计功能
"""
import json
import os
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Any
from datetime import datetime
from collections import defaultdict
from utils.logger import get_logger
from agent.environment.basic_info import BlockPosition, Position

logger = get_logger("BlockCache")


class CachedBlock:
    """缓存的方块信息"""
    def __init__(self, block_type: str, position: BlockPosition, last_seen: datetime, first_seen: datetime, seen_count: int = 1) -> None:
        self.block_type = block_type
        self.position = position
        self.last_seen = last_seen
        self.first_seen = first_seen
        self.seen_count = seen_count
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "block_type": self.block_type,
            "position": self.position.to_dict(),
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


class BlockCache:
    """方块缓存管理器"""
    def __init__(self, cache_file: str = None, auto_save_interval: int = None):
        """
        初始化方块缓存
        
        Args:
            cache_file: 缓存文件路径，如果为None则使用默认路径
            auto_save_interval: 自动保存间隔（秒），如果为None则从配置文件读取或使用默认值30秒
        """
        # 主缓存：位置 -> 方块信息
        self._position_cache: Dict[BlockPosition, CachedBlock] = dict()
        
        # 类型索引：方块类型 -> 位置集合
        self._type_index: Dict[str, Set[BlockPosition]] = defaultdict(set)
        
        # 名称索引：方块名称 -> 位置集合
        self._name_index: Dict[str, Set[BlockPosition]] = defaultdict(set)
        
        # 玩家位置缓存 - 使用字典存储每个玩家的最新位置，键为玩家名称
        self._player_position_cache: Dict[str, PlayerPositionCache] = {}
        
        # 统计信息
        self._stats = {
            "total_blocks_cached": 0,
            "total_updates": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_player_positions": 0,
            "last_cleanup": datetime.now()
        }
        
        # 缓存文件配置
        if cache_file is None:
            # 使用默认路径：main.py同级目录下的cache子目录
            main_dir = Path(__file__).parent.parent.parent
            cache_dir = main_dir / "data"
            cache_dir.mkdir(exist_ok=True)
            self._cache_file = cache_dir / "block_cache.json"
            self._player_cache_file = cache_dir / "player_position_cache.json"
        else:
            self._cache_file = Path(cache_file)
            self._player_cache_file = self._cache_file.parent / "player_position_cache.json"
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 自动保存间隔配置
        if auto_save_interval is None:
            self._auto_save_interval = self._get_config_auto_save_interval()
        else:
            self._auto_save_interval = auto_save_interval
        
        self._auto_save_task = None
        
        # 从文件加载缓存
        self._load_cache()
        self._load_player_cache()
        
        # 启动自动保存任务
        self._start_auto_save()
        
        logger.info(f"方块缓存系统初始化完成，缓存文件：{self._cache_file}")
        logger.info(f"玩家位置缓存文件：{self._player_cache_file}")
        logger.info(f"自动保存间隔：{self._auto_save_interval}秒")
    
    def _get_config_auto_save_interval(self) -> int:
        """从配置文件读取自动保存间隔"""
        try:
            # 尝试读取配置文件
            config_file = Path(__file__).parent.parent.parent.parent / "config.toml"
            if config_file.exists():
                import tomllib
                with open(config_file, 'rb') as f:
                    config = tomllib.load(f)
                
                block_cache_config = config.get("block_cache", {})
                return block_cache_config.get("auto_save_interval", 30)
        except Exception as e:
            logger.debug(f"读取配置文件失败，使用默认值: {e}")
        
        return 30  # 默认30秒
    
    def _load_cache(self):
        """从文件加载缓存"""
        try:
            if self._cache_file.exists():
                # 尝试加载缓存文件
                try:
                    with open(self._cache_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except json.JSONDecodeError as json_error:
                    logger.error(f"JSON解析错误: {json_error}")
                    # 尝试修复损坏的缓存文件
                    if self._try_repair_cache():
                        # 重新尝试加载
                        with open(self._cache_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                    else:
                        # 如果修复失败，创建新的缓存文件
                        logger.warning("缓存文件损坏且无法修复，将创建新的缓存文件")
                        self._create_new_cache_file()
                        return
                except Exception as e:
                    logger.error(f"读取缓存文件失败: {e}")
                    return
                
                # 加载方块数据
                blocks_data = data.get("blocks", {})
                loaded_count = 0
                
                for pos_key, block_data in blocks_data.items():
                    try:
                        # 解析位置键 "x,y,z"
                        x, y, z = map(int, pos_key.split(','))
                        position = BlockPosition({"x": x, "y": y, "z": z})
                        
                        # 创建缓存方块对象
                        cached_block = CachedBlock.from_dict(block_data)
                        
                        # 添加到缓存
                        self._position_cache[position] = cached_block
                        self._type_index[cached_block.block_type].add(position)
                        
                        loaded_count += 1
                    except Exception as e:
                        logger.warning(f"加载方块缓存数据失败 {pos_key}: {e}")
                        continue
                
                # 加载统计信息
                stats_data = data.get("stats", {})
                if stats_data:
                    for key, value in stats_data.items():
                        if key in self._stats:
                            if key in ["last_cleanup"] and isinstance(value, str):
                                try:
                                    self._stats[key] = datetime.fromisoformat(value)
                                except:
                                    pass
                            else:
                                self._stats[key] = value
                
                logger.info(f"从文件加载了 {loaded_count} 个方块缓存")
            else:
                logger.info("缓存文件不存在，将创建新的缓存")
        except Exception as e:
            logger.error(f"加载缓存文件失败: {e}")
            # 如果加载失败，创建新的缓存文件
            self._create_new_cache_file()
    
    def _load_player_cache(self):
        """从文件加载玩家位置缓存"""
        try:
            if self._player_cache_file.exists():
                try:
                    with open(self._player_cache_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except json.JSONDecodeError as json_error:
                    logger.error(f"玩家位置缓存JSON解析错误: {json_error}")
                    return
                except Exception as e:
                    logger.error(f"读取玩家位置缓存文件失败: {e}")
                    return
                
                # 加载玩家位置数据
                positions_data = data.get("player_positions", [])
                loaded_count = 0
                
                for pos_data in positions_data:
                    try:
                        player_pos = PlayerPositionCache.from_dict(pos_data)
                        # 使用玩家名称作为键，只保留最新数据
                        self._player_position_cache[player_pos.player_name] = player_pos
                        loaded_count += 1
                    except Exception as e:
                        logger.warning(f"加载玩家位置缓存数据失败: {e}")
                        continue
                
                # 更新统计信息
                self._stats["total_player_positions"] = len(self._player_position_cache)
                
                logger.info(f"从文件加载了 {loaded_count} 个玩家位置缓存")
            else:
                logger.info("玩家位置缓存文件不存在，将创建新的缓存")
                self._create_new_player_cache_file()
        except Exception as e:
            logger.error(f"加载玩家位置缓存文件失败: {e}")
            # 如果加载失败，创建新的缓存文件
            self._create_new_player_cache_file()
    
    def _create_new_player_cache_file(self):
        """创建新的空玩家位置缓存文件"""
        try:
            new_cache_data = {
                "player_positions": [],
                "last_save": datetime.now().isoformat(),
                "cache_version": "1.0"
            }
            
            with open(self._player_cache_file, 'w', encoding='utf-8') as f:
                json.dump(new_cache_data, f, ensure_ascii=False, indent=2)
            
            logger.info("已创建新的玩家位置缓存文件")
        except Exception as e:
            logger.error(f"创建新玩家位置缓存文件失败: {e}")
    
    def _try_repair_cache(self) -> bool:
        """尝试修复损坏的缓存文件"""
        try:
            import shutil
            from pathlib import Path
            
            # 备份原文件
            backup_path = self._cache_file.with_suffix('.json.backup')
            shutil.copy2(self._cache_file, backup_path)
            logger.info(f"已备份损坏的缓存文件到: {backup_path}")
            
            # 尝试修复
            with open(self._cache_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找最后一个完整的JSON对象
            last_brace_pos = content.rfind('}')
            if last_brace_pos != -1:
                try:
                    # 尝试解析到最后一个完整对象
                    partial_content = content[:last_brace_pos + 1]
                    json.loads(partial_content)
                    
                    # 写入修复后的内容
                    with open(self._cache_file, 'w', encoding='utf-8') as f:
                        f.write(partial_content)
                    
                    logger.info("缓存文件修复成功")
                    return True
                except:
                    pass
            
            # 如果修复失败，恢复备份文件
            shutil.copy2(backup_path, self._cache_file)
            logger.warning("缓存文件修复失败，已恢复原文件")
            return False
            
        except Exception as e:
            logger.error(f"修复缓存文件时出错: {e}")
            return False
    
    def _create_new_cache_file(self):
        """创建新的空缓存文件"""
        try:
            new_cache_data = {
                "blocks": {},
                "stats": {
                    "total_blocks_cached": 0,
                    "total_updates": 0,
                    "cache_hits": 0,
                    "cache_misses": 0,
                    "total_player_positions": 0,
                    "last_cleanup": datetime.now().isoformat()
                },
                "last_save": datetime.now().isoformat(),
                "cache_version": "1.0"
            }
            
            with open(self._cache_file, 'w', encoding='utf-8') as f:
                json.dump(new_cache_data, f, ensure_ascii=False, indent=2)
            
            logger.info("已创建新的缓存文件")
        except Exception as e:
            logger.error(f"创建新缓存文件失败: {e}")
    
    def _save_cache(self):
        """保存缓存到文件"""
        try:
            # 准备保存数据
            save_data = {
                "blocks": {},
                "stats": self._serialize_stats(),
                "last_save": datetime.now().isoformat(),
                "cache_version": "1.0"
            }
            
            # 转换方块数据为可序列化格式
            for position, block in self._position_cache.items():
                pos_key = f"{position.x},{position.y},{position.z}"
                save_data["blocks"][pos_key] = block.to_dict()
            
            # 保存到文件
            with open(self._cache_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"缓存已保存到文件: {self._cache_file}")
        except Exception as e:
            logger.error(f"保存缓存文件失败: {e}")
    
    def _save_player_cache(self):
        """保存玩家位置缓存到文件"""
        try:
            # 准备保存数据
            save_data = {
                "player_positions": [],
                "last_save": datetime.now().isoformat(),
                "cache_version": "1.0"
            }
            
            # 转换玩家位置数据为可序列化格式
            for player_pos in self._player_position_cache.values():
                save_data["player_positions"].append(player_pos.to_dict())
            
            # 保存到文件
            with open(self._player_cache_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"玩家位置缓存已保存到文件: {self._player_cache_file}")
        except Exception as e:
            logger.error(f"保存玩家位置缓存文件失败: {e}")
    
    def _serialize_stats(self) -> dict:
        """序列化统计信息，将datetime对象转换为字符串"""
        serialized_stats = {}
        for key, value in self._stats.items():
            if isinstance(value, datetime):
                serialized_stats[key] = value.isoformat()
            else:
                serialized_stats[key] = value
        return serialized_stats
    
    def _start_auto_save(self):
        """启动自动保存任务"""
        async def auto_save_loop():
            while True:
                try:
                    await asyncio.sleep(self._auto_save_interval)
                    self._save_cache()
                    self._save_player_cache()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"自动保存任务出错: {e}")
        
        # 创建异步任务
        try:
            loop = asyncio.get_event_loop()
            self._auto_save_task = loop.create_task(auto_save_loop())
        except RuntimeError:
            # 如果没有事件循环，使用asyncio.create_task
            self._auto_save_task = asyncio.create_task(auto_save_loop())
        
        logger.info("自动保存任务已启动")
    
    def stop_auto_save(self):
        """停止自动保存任务"""
        if self._auto_save_task and not self._auto_save_task.done():
            self._auto_save_task.cancel()
            logger.info("自动保存任务已停止")
    
    def force_save(self):
        """强制保存缓存"""
        logger.info("强制保存缓存...")
        self._save_cache()
        self._save_player_cache()
    
    def clear_cache(self):
        """清空缓存"""
        self._position_cache.clear()
        self._type_index.clear()
        self._name_index.clear()
        self._player_position_cache.clear()
        
        # 重置统计信息
        self._stats = {
            "total_blocks_cached": 0,
            "total_updates": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_player_positions": 0,
            "last_cleanup": datetime.now()
        }
        
        logger.info("缓存已清空")
    
    def __del__(self):
        """析构函数，确保保存缓存"""
        try:
            self.stop_auto_save()
            self._save_cache()
            self._save_player_cache()
        except:
            pass
    
    def update_player_position(self, player_name: str, position: Position, yaw: float, pitch: float) -> PlayerPositionCache:
        """
        更新玩家位置和视角信息（只保留最新位置）
        
        Args:
            player_name: 玩家名称
            position: 玩家位置
            yaw: 水平视角
            pitch: 垂直视角
            
        Returns:
            缓存的玩家位置对象
        """
        now = datetime.now()
        
        # 创建新的玩家位置缓存
        player_pos = PlayerPositionCache(
            player_name=player_name,
            position=position,
            yaw=yaw,
            pitch=pitch,
            timestamp=now
        )
        
        # 更新或添加玩家位置（覆盖旧数据）
        self._player_position_cache[player_name] = player_pos
        
        # 更新统计信息（总玩家数量）
        self._stats["total_player_positions"] = len(self._player_position_cache)
        
        logger.debug(f"更新玩家位置缓存: {player_name} at ({position.x:.2f}, {position.y:.2f}, {position.z:.2f})")
        return player_pos
    
    def get_player_positions(self, player_name: str = None, limit: int = None) -> List[PlayerPositionCache]:
        """
        获取玩家位置信息（每个玩家只保留最新位置）
        
        Args:
            player_name: 玩家名称，如果为None则返回所有玩家的最新位置
            limit: 限制返回的玩家数量，如果为None则返回所有玩家
            
        Returns:
            玩家位置记录列表
        """
        if player_name:
            # 获取特定玩家的最新位置
            if player_name in self._player_position_cache:
                return [self._player_position_cache[player_name]]
            else:
                return []
        else:
            # 返回所有玩家的最新位置
            positions = list(self._player_position_cache.values())
            
            # 按时间戳排序（最新的在前）
            positions.sort(key=lambda x: x.timestamp, reverse=True)
            
            # 限制返回数量
            if limit:
                positions = positions[:limit]
            
            return positions
    
    def get_latest_player_position(self, player_name: str) -> Optional[PlayerPositionCache]:
        """
        获取玩家的位置信息（每个玩家只保留最新位置）
        
        Args:
            player_name: 玩家名称
            
        Returns:
            玩家的位置信息，如果不存在则返回None
        """
        return self._player_position_cache.get(player_name)
    
    def update_from_blocks(self, blocks_data: Dict[str, Any]) -> int:
        """
        从query_surroundings函数的结果更新方块缓存
        
        Args:
            query_result: query_surroundings函数返回的结果字典
            
        Returns:
            更新的方块数量
        """
        if not blocks_data:
            logger.debug("query_surroundings返回的方块数据为空")
            return 0
        
        
        updated_count = 0
        try:
            observed_positions: Set[Tuple[int, int, int]] = set()
            min_x = min_y = min_z = None
            max_x = max_y = max_z = None
            for block_type, block_info in blocks_data["blockMap"].items():
                positions = block_info.get("positions", [])
                for pos in positions:
                    x, y, z = int(pos[0]), int(pos[1]), int(pos[2])
                    pos = {"x": x, "y": y, "z": z}
                    self.add_block(block_type, BlockPosition(pos))
                    observed_positions.add((x, y, z))
                    # 更新边界
                    min_x = x if min_x is None else min(min_x, x)
                    max_x = x if max_x is None else max(max_x, x)
                    min_y = y if min_y is None else min(min_y, y)
                    max_y = y if max_y is None else max(max_y, y)
                    min_z = z if min_z is None else min(min_z, z)
                    max_z = z if max_z is None else max(max_z, z)
                    updated_count += 1

            # 以观测到的最小/最大 xyz 创建包围盒，填充缺失为 air
            if observed_positions and None not in (min_x, max_x, min_y, max_y, min_z, max_z):
                for ix in range(min_x, max_x + 1):
                    for iy in range(min_y, max_y + 1):
                        for iz in range(min_z, max_z + 1):
                            if (ix, iy, iz) not in observed_positions:
                                pos = {"x": ix, "y": iy, "z": iz}
                                self.add_block("air", BlockPosition(pos))
                                updated_count += 1

            # logger.info(f"从query_surroundings更新了 {updated_count} 个方块到缓存")
            return updated_count
        except Exception as e:
            logger.error(f"处理query_surroundings数据时出错: {e}")
            return 0
        
    
    def add_block(self, block_type: str, position: BlockPosition) -> CachedBlock:
        """
        添加或更新方块信息
        
        Args:
            block_type: 方块类型
            position: 方块位置
            
        Returns:
            缓存的方块对象
        """
        now = datetime.now()
        # logger.info(f"添加方块缓存: {block_type} at ({position.x}, {position.y}, {position.z})")
        # logger.info(f"方块缓存: {self._position_cache}")
        
        if position in self._position_cache:
            # 更新现有方块
            existing_block = self._position_cache[position]
            existing_block.block_type = block_type
            existing_block.last_seen = now
            existing_block.seen_count += 1
            
            # 更新索引
            self._update_indices(existing_block, block_type)
            
            self._stats["total_updates"] += 1
            
            return existing_block
        else:
            # 添加新方块
            new_block = CachedBlock(
                block_type=block_type,
                position=position,
                last_seen=now,
                first_seen=now
            )
            
            self._position_cache[position] = new_block
            self._type_index[block_type].add(position)
            
            self._stats["total_blocks_cached"] += 1
            self._stats["total_updates"] += 1
            
            return new_block
    
    def get_block(self, x: int, y: int, z: int) -> Optional[CachedBlock]:
        """
        获取指定位置的方块信息
        
        Args:
            x, y, z: 坐标位置
            
        Returns:
            方块信息，如果不存在则返回None
        """
        position = BlockPosition({"x": x, "y": y, "z": z})
        
        if position in self._position_cache:
            self._stats["cache_hits"] += 1
            return self._position_cache[position]
        else:
            self._stats["cache_misses"] += 1
            return None
    
    def get_blocks_by_type(self, block_type: str) -> List[CachedBlock]:
        """
        获取指定类型的所有方块
        
        Args:
            block_type: 方块类型名称
            
        Returns:
            方块列表
        """
        positions = self._type_index.get(block_type, set())
        return [self._position_cache[pos] for pos in positions if pos in self._position_cache]
    
    def get_blocks_in_range(self, center_x: float, center_y: float, center_z: float, 
                           radius: float) -> List[CachedBlock]:
        """
        获取指定范围内的所有方块
        
        Args:
            center_x, center_y, center_z: 中心点坐标
            radius: 搜索半径
            
        Returns:
            范围内的方块列表
        """
        radius_squared = radius * radius
        blocks_in_range = []
        
        for block in self._position_cache.values():
            dx = block.position.x - center_x
            dy = block.position.y - center_y
            dz = block.position.z - center_z
            distance_squared = dx*dx + dy*dy + dz*dz
            
            if distance_squared <= radius_squared:
                blocks_in_range.append(block)
        
        return blocks_in_range
    
    def remove_block(self, x: float, y: float, z: float) -> bool:
        """
        移除指定位置的方块缓存
        
        Args:
            x, y, z: 坐标位置
            
        Returns:
            是否成功移除
        """
        position = BlockPosition({"x": x, "y": y, "z": z})
        
        if position not in self._position_cache:
            return False
        
        block = self._position_cache[position]
        
        # 从主缓存移除
        del self._position_cache[position]
        
        # 从索引中移除
        self._type_index[block.block_type].discard(position)
        
        # 清理空的索引项
        if not self._type_index[block.block_type]:
            del self._type_index[block.block_type]
        
        logger.debug(f"移除方块缓存: {block.block_type} at ({x}, {y}, {z})")
        return True
    
    
    def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        return {
            **self._stats,
            "current_cache_size": len(self._position_cache),
            "type_count": len(self._type_index),
            "cache_hit_rate": (self._stats["cache_hits"] / 
                              max(1, self._stats["cache_hits"] + self._stats["cache_misses"])),
            "player_position_count": len(self._player_position_cache)
        }
    
    def _update_indices(self, block: CachedBlock, new_type: str):
        """更新索引信息"""
        old_type = block.block_type
        
        # 如果类型或名称发生变化，需要更新索引
        if old_type != new_type:
            self._type_index[old_type].discard(block.position)
            if not self._type_index[old_type]:
                del self._type_index[old_type]
            self._type_index[new_type].add(block.position)
    
    def __len__(self) -> int:
        """返回缓存的方块数量"""
        return len(self._position_cache)
    
    def __contains__(self, position: BlockPosition) -> bool:
        """检查指定位置是否有缓存的方块"""
        return position in self._position_cache
    
# 全局实例
global_block_cache = BlockCache()