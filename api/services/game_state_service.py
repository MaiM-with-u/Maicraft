"""
游戏状态服务
管理游戏数据的获取、格式化和推送
"""

import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from agent.environment.environment import global_environment
from agent.block_cache.block_cache import global_block_cache
from agent.container_cache.container_cache import global_container_cache
from agent.environment.locations import global_location_points
from utils.logger import get_logger


class GameStateService:
    """游戏状态服务"""

    def __init__(self):
        self.logger = get_logger("GameStateService")

    def get_player_data(self) -> Dict[str, Any]:
        """获取玩家数据"""
        env = global_environment

        # 格式化装备信息
        equipment = {}
        if env.equipment:
            for slot_name, item_data in env.equipment.items():
                if item_data:
                    equipment[slot_name] = {
                        "name": item_data.get("name", ""),
                        "count": item_data.get("count", 1),
                        "damage": 0,
                        "max_durability": 0
                    }
                    # 获取耐久度信息
                    max_durability = item_data.get("maxDurability", 0)
                    if max_durability > 0:
                        equipment[slot_name]["max_durability"] = max_durability
                        # 计算已使用耐久度
                        if item_data.get("components"):
                            for component in item_data["components"]:
                                if component.get("type") == "damage":
                                    equipment[slot_name]["damage"] = component.get("data", 0)
                                    break

        # 格式化物品栏信息
        inventory = {
            "occupied_slots": env.occupied_slot_count,
            "total_slots": env.slot_count,
            "empty_slots": env.empty_slot_count,
            "items": []
        }

        for item in env.inventory:
            if isinstance(item, dict) and item.get("count", 0) > 0:
                item_data = {
                    "slot": item.get("slot", 0),
                    "name": item.get("name", ""),
                    "display_name": item.get("displayName", item.get("name", "")),
                    "count": item.get("count", 1),
                    "max_stack": 64,  # 默认最大堆叠数
                    "damage": 0,
                    "max_durability": 0
                }

                # 处理耐久度信息
                max_durability = item.get("maxDurability", 0)
                if max_durability > 0:
                    item_data["max_durability"] = max_durability
                    # 计算已使用耐久度
                    if item.get("components"):
                        for component in item["components"]:
                            if component.get("type") == "damage":
                                item_data["damage"] = component.get("data", 0)
                                break

                inventory["items"].append(item_data)

        position_data = {}
        if env.position:
            position_data = {
                "x": env.position.x,
                "y": env.position.y,
                "z": env.position.z,
                "yaw": env.yaw or 0.0,
                "pitch": env.pitch or 0.0,
                "on_ground": env.on_ground
            }

        return {
            "name": env.player_name,
            "health": env.health,
            "max_health": env.health_max,
            "food": env.food,
            "max_food": env.food_max,
            "experience": env.experience,
            "level": env.level,
            "position": position_data,
            "gamemode": env.gamemode,
            "equipment": equipment,
            "inventory": inventory
        }

    def get_world_data(self) -> Dict[str, Any]:
        """获取世界数据"""
        env = global_environment

        # 格式化时间
        time_of_day = env.time_of_day
        formatted_time = self._format_time_of_day(time_of_day)

        # 格式化天气
        weather = env.weather.lower() if env.weather else "clear"
        formatted_weather = self._format_weather(weather)

        # 获取光照等级
        light_level = 15  # 默认值
        if env.position:
            block_pos = env.block_position
            if block_pos:
                # 这里可以添加获取光照等级的逻辑
                pass

        # 获取附近方块信息
        nearby_blocks = []
        if env.position:
            # 获取玩家周围的方块信息
            radius = 5
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    for dz in range(-radius, radius + 1):
                        if dx == 0 and dy == 0 and dz == 0:
                            continue
                        block = global_block_cache.get_block(
                            env.position.x + dx,
                            env.position.y + dy,
                            env.position.z + dz
                        )
                        if block:
                            distance = (dx**2 + dy**2 + dz**2)**0.5
                            nearby_blocks.append({
                                "name": block.block_type,
                                "position": {
                                    "x": block.position.x,
                                    "y": block.position.y,
                                    "z": block.position.z
                                },
                                "distance": round(distance, 2)
                            })

            # 限制数量，避免数据过大
            nearby_blocks = sorted(nearby_blocks, key=lambda x: x["distance"])[:20]

        # 获取附近实体信息
        nearby_entities = []
        for entity in env.nearby_entities:
            entity_data = {
                "name": entity.name,
                "display_name": entity.name,
                "type": entity.type,
                "distance": entity.distance or 0.0,
                "position": {
                    "x": entity.position.x,
                    "y": entity.position.y,
                    "z": entity.position.z
                }
            }
            if hasattr(entity, 'health') and entity.health is not None:
                entity_data["health"] = entity.health
                entity_data["max_health"] = entity.max_health or entity.health

            nearby_entities.append(entity_data)

        return {
            "time": {
                "time_of_day": time_of_day,
                "formatted_time": formatted_time,
                "day_count": time_of_day // 24000 if time_of_day else 0
            },
            "weather": {
                "weather": weather,
                "formatted_weather": formatted_weather,
                "duration": 0  # 需要额外逻辑获取天气持续时间
            },
            "location": {
                "dimension": env.dimension or "overworld",
                "biome": env.biome or "unknown",
                "light_level": light_level
            },
            "nearby_blocks": nearby_blocks,
            "nearby_entities": nearby_entities
        }

    def get_marker_data(self) -> Dict[str, Any]:
        """获取标记点数据"""
        # 这里可以实现标记点数据的获取逻辑
        # 目前返回空数据，等待后续实现
        return {
            "markers": []
        }

    def get_environment_snapshot(self) -> Dict[str, Any]:
        """获取环境快照"""
        return {
            "player": self.get_player_data(),
            "world": self.get_world_data(),
            "markers": self.get_marker_data(),
            "timestamp": int(time.time() * 1000)
        }

    def get_player_info(self) -> Dict[str, Any]:
        """获取玩家信息"""
        return self.get_player_data()

    def get_inventory_info(self) -> Dict[str, Any]:
        """获取物品栏信息"""
        player_data = self.get_player_data()
        return player_data.get("inventory", {})

    def get_world_info(self) -> Dict[str, Any]:
        """获取世界信息"""
        return self.get_world_data()

    def get_nearby_entities(self, range_limit: int = 16) -> List[Dict[str, Any]]:
        """获取附近实体"""
        world_data = self.get_world_data()
        entities = world_data.get("nearby_entities", [])

        # 按距离过滤
        filtered_entities = [
            entity for entity in entities
            if entity.get("distance", 0) <= range_limit
        ]

        return filtered_entities

    def _format_time_of_day(self, time_of_day: int) -> str:
        """格式化时间显示"""
        if time_of_day is None:
            return "未知"

        # Minecraft时间计算 (0-23999)
        if 0 <= time_of_day < 6000:
            return "夜晚"
        elif 6000 <= time_of_day < 12000:
            return "白天"
        elif 12000 <= time_of_day < 18000:
            return "黄昏"
        else:
            return "夜晚"

    def _format_weather(self, weather: str) -> str:
        """格式化天气显示"""
        weather_map = {
            "clear": "晴朗",
            "rain": "下雨",
            "thunder": "雷雨",
            "snow": "下雪"
        }
        return weather_map.get(weather, "未知")


# 全局游戏状态服务实例
game_state_service = GameStateService()