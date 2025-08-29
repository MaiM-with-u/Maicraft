"""
Minecraft环境信息存储类
用于存储和管理游戏环境数据
"""

from dataclasses import field
from typing import List, Dict, Any, Optional
from datetime import datetime
from utils.logger import get_logger
from .basic_info import Player, Position, Entity, Event, BlockPosition
from agent.block_cache.block_cache import global_block_cache
from openai_client.llm_request import LLMClient

logger = get_logger("EnvironmentInfo")

class EnvironmentInfo:
    """Minecraft环境信息存储类"""
    
    def __init__(self):
        # 玩家信息
        self.player_name: str = ""
        self.gamemode: str = ""  # 新增：游戏模式
        
        # 位置信息(脚)
        self.position: Optional[Position] = None
        self.block_position: Optional[BlockPosition] = None
        
        # 速度信息
        self.velocity: Optional[Position] = None  # 新增：速度向量
        
        # 光标信息
        self.block_at_cursor: Optional[Dict[str, Any]] = None  # 新增：光标指向的方块
        self.entity_at_cursor: Optional[Dict[str, Any]] = None  # 新增：光标指向的实体
        self.held_item: Optional[Dict[str, Any]] = None  # 新增：手持物品
        self.using_held_item: bool = False  # 新增：是否正在使用手持物品
        
        # 状态信息
        self.health: int = 0
        self.health_max: int = 20
        self.health_percentage: int = 0
        self.food: int = 0
        self.food_max: int = 20
        self.food_saturation: int = 0
        self.food_percentage: int = 0
        self.experience: int = 0
        self.level: int = 0
        self.oxygen: int = 0
        self.armor: int = 0  # 新增：护甲值
        self.is_sleeping: bool = False  # 新增：是否在睡觉
        self.on_ground: bool = True  # 新增：是否在地面上
        
        # 视角信息
        self.yaw: float = 0.0  # 新增：水平视角
        self.pitch: float = 0.0  # 新增：垂直视角
        
        # 装备信息
        self.equipment: Dict[str, Optional[Dict[str, Any]]] = {}  # 新增：装备信息

        self.overview_base64 = ""
        self.overview_str = ""
        
        # 物品栏
        self.inventory: List[Any] = []
        
        self.occupied_slot_count: int = 0
        self.empty_slot_count: int = 0
        self.slot_count: int = 0
        
        
        # 环境信息
        self.weather: str = ""
        self.time_of_day: int = 0
        self.dimension: str = ""
        self.biome: str = ""  # 新增：生物群系
        
        # 附近玩家
        self.nearby_players: List[Player] = []
        
        # 附近实体
        self.nearby_entities: List[Entity] = []
        
        
        # 最近事件
        self.recent_events: List[Event] = []
        
        # 系统状态
        self.status: str = ""
        self.request_id: str = ""
        self.elapsed_ms: int = 0
        
        # 时间戳
        self.last_update: Optional[datetime] = None
        
    def set_vlm(self, vlm: LLMClient):
        self.vlm = vlm
        
    async def get_overview_str(self) -> str:
        if not self.vlm:
            return ""
        prompt = """
你是一个经验丰富的Minecraft玩家，现在你正在一个Minecraft世界中，请根据你看到的画面，描述你周围的环境。
黄色箭头代表玩家位置，黄色线条代表了玩家走过的路线
周围黑色的区域代表还未探索的区域，不是没有方块的区域
请你根据这幅鸟瞰图大致描述 xyz各个方向的地形和物品 
        """
        
        logger.info(f"prompt: {prompt}")
        result = await self.vlm.simple_vision(prompt, self.overview_base64)
        self.overview_str = result
        return result
        

    def update_from_observation(self, observation_data: Dict[str, Any]) -> None:
        """从观察数据更新环境信息"""
        if not observation_data.get("ok"):
            return
        
        data = observation_data.get("data", {})

        
        # 更新游戏状态信息 (来自 query_game_state)
        self.weather = data.get("weather", "")
        self.time_of_day = data.get("timeOfDay", 0)
        self.dimension = data.get("dimension", "")
        self.biome = data.get("biome", "") # 更新生物群系
        
        self.player_name = data.get("username", "")
        self.gamemode = data.get("gamemode", "") # 更新游戏模式
        
        # 更新在线玩家信息 (来自 query_game_state)
        online_players = data.get("onlinePlayers", [])
        self.nearby_players = []
        for player_name in online_players:
            # 在线玩家只提供名称，创建基本的Player对象
            player = Player(
                uuid="",  # 在线玩家列表中没有UUID
                username=player_name,
                display_name=player_name,
                ping=0,  # 在线玩家列表中没有ping信息
                gamemode=0  # 在线玩家列表中没有游戏模式信息
            )
            self.nearby_players.append(player)
    
        
        # 更新位置信息
        pos_data = data.get("position")
        if pos_data and isinstance(pos_data, dict):
            self.position = Position(
                x=pos_data.get("x", 0.0),
                y=pos_data.get("y", 0.0),
                z=pos_data.get("z", 0.0)
            )
        else:
            # 如果没有位置数据，设置为默认位置或保持为None
            self.position = None
            logger.warning("未找到有效的位置数据，位置信息未更新")
            
        self.block_position = BlockPosition(self.position)
        
        # 更新速度信息
        velocity_data = data.get("velocity")
        if velocity_data and isinstance(velocity_data, dict):
            self.velocity = Position(
                x=velocity_data.get("x", 0.0),
                y=velocity_data.get("y", 0.0),
                z=velocity_data.get("z", 0.0)
            )
        else:
            self.velocity = None
        
        # 更新状态信息
        health_data = data.get("health", {})
        self.health = health_data.get("current", 0)
        self.health_max = health_data.get("max", 20)
        self.health_percentage = health_data.get("percentage", 0)
        
        food_data = data.get("food", {})
        self.food = food_data.get("current", 0)
        self.food_max = food_data.get("max", 20)
        self.food_saturation = food_data.get("saturation", 0)
        self.food_percentage = food_data.get("percentage", 0)

        experience_data = data.get("experience", {})
        self.experience = experience_data.get("points", 0)
        self.level = experience_data.get("level", 0)
        
        self.oxygen = data.get("oxygen", 0)
        self.armor = data.get("armor", 0) # 更新护甲值
        self.is_sleeping = data.get("isSleeping", False) # 更新睡眠状态
        self.on_ground = data.get("onGround", True) # 更新是否在地面上
        
        # 更新视角信息
        self.yaw = data.get("yaw", 0.0)
        self.pitch = data.get("pitch", 0.0)
        
        # 更新装备信息
        self.equipment = data.get("equipment", {})
        
        # 更新手持物品信息
        self.held_item = data.get("heldItem")
        self.using_held_item = data.get("usingHeldItem", False)
        
        # 更新光标指向的方块和实体
        self.block_at_cursor = data.get("blockAtCursor") or data.get("blockAtEntityCursor")
        self.entity_at_cursor = data.get("entityAtCursor")
        
        
        # 更新物品栏
        inventory_data = data.get("inventory", {})
        self.inventory = [] 

        # 新格式：包含统计信息和槽位数据
        slots = inventory_data.get("slots", [])
        if isinstance(slots, list):
            for slot_data in slots:
                if isinstance(slot_data, dict):
                    # 构建标准化的物品信息
                    item_info = {
                        'slot': slot_data.get('slot', 0),
                        'count': slot_data.get('count', 0),
                        'name': slot_data.get('name', ''),
                        'displayName': slot_data.get('name', '')  # 使用name作为displayName
                    }
                    self.inventory.append(item_info)
        
        # 记录物品栏统计信息
        self.occupied_slot_count = inventory_data.get('fullSlotCount', 0)
        self.empty_slot_count = inventory_data.get('emptySlotCount', 0)
        self.slot_count = inventory_data.get('slotCount', 0)
        


        # 更新最近事件 (来自 query_recent_events)
        new_events = data.get("recentEvents", [])
        # logger.info(f"新增事件数量: {len(new_events)}")
        
        # 确保 recent_events 是列表类型
        if not isinstance(self.recent_events, list):
            logger.warning("recent_events 不是列表类型，重新初始化为空列表")
            self.recent_events = []
        
        # 将新事件添加到现有事件列表中，而不是清空重写
        for event_data in new_events:

            
            try:
                # 确定玩家名称
                player_name = ""
                if event_data.get("playerInfo"):
                    player_name = event_data["playerInfo"].get("username", "")
                elif event_data.get("player"):
                    player_name = event_data["player"].get("username", "")
                elif event_data.get("chatInfo"):
                    player_name = event_data["chatInfo"].get("username", "")
                
                event = Event(
                    type=event_data.get("type", ""),
                    timestamp=event_data.get("gameTick", 0),  # 使用gameTick作为时间戳
                    server_id="",  # 新格式中没有serverId
                    player_name=player_name
                )
                
                # 根据事件类型设置特定属性
                if event_data.get("player"):
                    player_data = event_data["player"]
                    event.player = Player(
                        uuid=player_data.get("uuid", ""),
                        username=player_data.get("username", ""),
                        display_name=player_data.get("displayName", ""),
                        ping=player_data.get("ping", 0),
                        gamemode=player_data.get("gamemode", 0)
                    )
                    # 设置玩家名称
                    event.player_name = player_data.get("username", "")
                
                # 处理playerInfo字段 (playerJoin事件)
                if event_data.get("playerInfo"):
                    player_info = event_data["playerInfo"]
                    event.player = Player(
                        uuid=player_info.get("uuid", ""),
                        username=player_info.get("username", ""),
                        display_name=player_info.get("displayName", ""),
                        ping=player_info.get("ping", 0),
                        gamemode=player_info.get("gamemode", 0)
                    )
                    # 设置玩家名称
                    event.player_name = player_info.get("username", "")
                
                # 处理位置信息 (playerRespawn事件)
                if event_data.get("position"):
                    pos_data = event_data["position"]
                    if isinstance(pos_data, dict):
                        event.new_position = Position(
                            x=pos_data.get("x", 0.0),
                            y=pos_data.get("y", 0.0),
                            z=pos_data.get("z", 0.0)
                        )
                    elif isinstance(pos_data, list) and len(pos_data) >= 3:
                        # 如果位置是列表格式 [x, y, z]
                        event.new_position = Position(
                            x=float(pos_data[0]) if pos_data[0] is not None else 0.0,
                            y=float(pos_data[1]) if pos_data[1] is not None else 0.0,
                            z=float(pos_data[2]) if pos_data[2] is not None else 0.0
                        )
                
                # 处理健康更新事件
                if event.type == "healthUpdate":
                    # 处理新的health格式
                    health_data = event_data.get("health", {})
                    if isinstance(health_data, dict):
                        event.health = health_data.get("current", 0)
                    else:
                        event.health = event_data.get("health", 0)
                    
                    # 处理新的food格式
                    food_data = event_data.get("food", {})
                    if isinstance(food_data, dict):
                        event.food = food_data.get("current", 0)
                        event.saturation = food_data.get("saturation", 0)
                    else:
                        event.food = event_data.get("food", 0)
                        event.saturation = event_data.get("saturation", 0)
                
                # 处理聊天事件
                if event.type == "chat" and event_data.get("chatInfo"):
                    chat_info = event_data["chatInfo"]
                    event.chat_text = chat_info.get("text", "")
                    # 确保玩家名称正确设置
                    if not event.player_name and chat_info.get("username"):
                        event.player_name = chat_info.get("username", "")
                    # 添加调试信息
                
                # 处理踢出事件
                if event.type == "playerKick" and event_data.get("reason"):
                    reason_data = event_data["reason"]
                    if isinstance(reason_data, dict) and reason_data.get("value", {}).get("translate"):
                        event.kick_reason = reason_data["value"]["translate"].get("value", "未知原因")
                    else:
                        event.kick_reason = str(reason_data)
                
                # 处理实体伤害事件
                if event.type == "entityHurt" and event_data.get("entity"):
                    entity_data = event_data["entity"]
                    event.entity_name = entity_data.get("name", "")
                    event.damage = event_data.get("damage", 0)
                    # 保存实体位置信息
                    if entity_data.get("position"):
                        pos_data = entity_data["position"]
                        if isinstance(pos_data, dict):
                            event.entity_position = Position(
                                x=pos_data.get("x", 0.0),
                                y=pos_data.get("y", 0.0),
                                z=pos_data.get("z", 0.0)
                            )
                
                # 处理实体死亡事件
                if event.type == "entityDeath" and event_data.get("entity"):
                    entity_data = event_data["entity"]
                    event.entity_name = entity_data.get("name", "")
                    # 保存实体位置信息
                    if entity_data.get("position"):
                        pos_data = entity_data["position"]
                        if isinstance(pos_data, dict):
                            event.entity_position = Position(
                                x=pos_data.get("x", 0.0),
                                y=pos_data.get("y", 0.0),
                                z=pos_data.get("z", 0.0)
                            )
                
                # 处理天气变化事件
                if event.type == "weatherChange":
                    event.weather = event_data.get("weather", "")
                
                self.recent_events.append(event)
            except Exception as e:
                # 记录事件处理错误，但继续处理其他事件
                import traceback
                print(f"处理事件数据时出错: {e}")
                print(f"事件数据: {event_data}")
                print(f"错误详情: {traceback.format_exc()}")
                continue
        
        # 限制事件列表大小，避免无限增长（保留最近1000个事件）
        if len(self.recent_events) > 1000:
            removed_count = len(self.recent_events) - 1000
            self.recent_events = self.recent_events[removed_count:]
            # logger.info(f"事件列表已限制大小，移除了 {removed_count} 个旧事件，当前事件总数: {len(self.recent_events)}")
        # else:
        #     logger.info(f"事件列表更新完成，当前事件总数: {len(self.recent_events)}")
        
        # 更新周围环境 - 玩家 (来自 query_surroundings("players"))
        if "nearbyPlayers" in data:
            nearby_players_data = data["nearbyPlayers"]
            if isinstance(nearby_players_data, list):
                # 如果nearbyPlayers是列表，直接使用
                self.nearby_players = []
                for player_data in nearby_players_data:
                    try:
                        if isinstance(player_data, dict):
                            player = Player(
                                uuid=player_data.get("uuid", ""),
                                username=player_data.get("username", ""),
                                display_name=player_data.get("displayName", ""),
                                ping=player_data.get("ping", 0),
                                gamemode=player_data.get("gamemode", 0)
                            )
                            self.nearby_players.append(player)
                        else:
                            # 如果只是玩家名称字符串
                            player = Player(
                                uuid="",
                                username=str(player_data),
                                display_name=str(player_data),
                                ping=0,
                                gamemode=0
                            )
                            self.nearby_players.append(player)
                    except Exception as e:
                        # 记录玩家处理错误，但继续处理其他玩家
                        import traceback
                        print(f"处理玩家数据时出错: {e}")
                        print(f"玩家数据: {player_data}")
                        print(f"错误详情: {traceback.format_exc()}")
                        continue
        
        # 更新周围环境 - 实体 (来自 query_surroundings("entities"))
        if "nearbyEntities" in data:
            nearby_entities_data = data["nearbyEntities"]
            if isinstance(nearby_entities_data, list):
                self.nearby_entities = []
                for entity_data in nearby_entities_data:
                    try:
                        if isinstance(entity_data, dict):
                            # 位置兼容：支持 {x,y,z} 与 [x,y,z]
                            position = Position(0.0, 0.0, 0.0)
                            if "position" in entity_data:
                                pos_data = entity_data["position"]
                                if isinstance(pos_data, dict):
                                    position = Position(
                                        x=pos_data.get("x", 0.0),
                                        y=pos_data.get("y", 0.0),
                                        z=pos_data.get("z", 0.0)
                                    )
                                elif isinstance(pos_data, list) and len(pos_data) >= 3:
                                    position = Position(
                                        x=float(pos_data[0]) if pos_data[0] is not None else 0.0,
                                        y=float(pos_data[1]) if pos_data[1] is not None else 0.0,
                                        z=float(pos_data[2]) if pos_data[2] is not None else 0.0
                                    )

                            # 字段兼容：优先取标准字段，不存在则回退
                            # name: name -> displayName -> type/kind -> "未知实体"
                            raw_name = (
                                entity_data.get("name")
                                or entity_data.get("displayName")
                                or entity_data.get("type")
                                or entity_data.get("kind")
                                or "未知实体"
                            )

                            # type: type -> kind -> "other"
                            raw_type = entity_data.get("type") or entity_data.get("kind") or "other"

                            # id: id -> entityId -> 尝试由(name+pos)派生稳定整数
                            raw_id = entity_data.get("id") or entity_data.get("entityId")
                            if raw_id is None:
                                try:
                                    stable_key = f"{raw_name}|{position.x:.3f},{position.y:.3f},{position.z:.3f}"
                                    raw_id = abs(hash(stable_key)) % 1000000
                                except Exception:
                                    raw_id = 0

                            entity = Entity(
                                id=int(raw_id) if isinstance(raw_id, (int, float, str)) and str(raw_id).isdigit() else 0,
                                type=str(raw_type),
                                name=str(raw_name),
                                position=position,
                                distance=(float(entity_data.get("distance")) if entity_data.get("distance") is not None else None),
                                health=(int(entity_data.get("health")) if entity_data.get("health") is not None else None),
                                max_health=(int(entity_data.get("maxHealth")) if entity_data.get("maxHealth") is not None else None)
                            )
                            self.nearby_entities.append(entity)
                    except Exception as e:
                        # 记录实体处理错误，但继续处理其他实体
                        import traceback
                        print(f"处理实体数据时出错: {e}")
                        print(f"实体数据: {entity_data}")
                        print(f"错误详情: {traceback.format_exc()}")
                        continue
        
        # 更新请求信息
        self.request_id = observation_data.get("request_id", "")
        self.elapsed_ms = observation_data.get("elapsed_ms", 0)
        
        # 更新时间戳
        self.last_update = datetime.now()
        
    def get_position_str(self) -> str:
        """获取位置信息"""
        if self.block_position:
            block_feet = global_block_cache.get_block(self.block_position.x, self.block_position.y, self.block_position.z)
            if block_feet:
                if block_feet.block_type == "water":
                    block_on_feet_str = f"注意：你正在水(x={self.block_position.x},y={self.block_position.y},z={self.block_position.z})中，可能会受到水流的影响"
                    
            block_on_feet = global_block_cache.get_block(self.block_position.x, self.block_position.y-1, self.block_position.z)
            if block_on_feet:
                block_on_feet_str = f"你正站在方块 {block_on_feet.block_type} (x={block_on_feet.position.x},y={block_on_feet.position.y},z={block_on_feet.position.z}) 的上方"
            else:
                block_on_feet_str = "注意：脚下没有方块，你可能在方块边缘或正在下坠"
        position_str = f"""
请注意：
你现在的坐标(脚所在的坐标)是：x={self.block_position.x}, y={self.block_position.y}, z={self.block_position.z}
{block_on_feet_str}
        """
        return position_str

    def get_summary(self) -> str:
        """以可读文本形式返回所有环境信息"""
        lines = []
        
        # 玩家信息
        if self.player_name:
            lines.append("【自身信息】")
            lines.append(f"  用户名: {self.player_name}")
            lines.append(f"  游戏模式: {self.gamemode}")
            # lines.append(f"  显示名: {self.player.display_name}")
            # lines.append(f"  游戏模式: {self._get_gamemode_name(self.player.gamemode)}")
            lines.append("")
        
        # 状态信息
        lines.append("【状态信息】")
        lines.append(f"  生命值: {self.health}/{self.health_max}")
        lines.append(f"  饥饿值: {self.food}/{self.food_max}")
        if self.food_saturation > 0:
            lines.append(f"  饥饿饱和度: {self.food_saturation}")
        # lines.append(f"  经验值: {self.experience}")
        lines.append(f"  等级: {self.level}")
        lines.append(f"  护甲值: {self.armor}")
        lines.append(f"  是否在地面上: {self.on_ground}")
        # lines.append(f"  是否在睡觉: {self.is_sleeping}")
        lines.append(f"  氧气: {self.oxygen}")
        
        # 视角信息
        # if self.yaw != 0.0 or self.pitch != 0.0:
        #     lines.append(f"  视角: Yaw={self.yaw:.2f}°, Pitch={self.pitch:.2f}°")
        
        # 速度信息
        # if self.velocity:
        #     lines.append(f"  速度: X={self.velocity.x:.2f}, Y={self.velocity.y:.2f}, Z={self.velocity.z:.2f}")
        
        # 手持物品信息
        if self.held_item:
            item_name = self.held_item.get("displayName", self.held_item.get("name", "未知物品"))
            item_count = self.held_item.get("count", 1)
            durability = self.held_item.get("maxDurability", 0)
            current_damage = 0
            if self.held_item.get("components"):
                for component in self.held_item["components"]:
                    if component.get("type") == "damage":
                        current_damage = component.get("data", 0)
                        break
            
            lines.append(f"  手持物品: {item_name} x{item_count}")
            if durability > 1:
                remaining_durability = durability - current_damage
                lines.append(f"    耐久度: {remaining_durability}/{durability}")
            if self.using_held_item:
                lines.append("    正在使用中")
        
        # 光标信息
        # if self.block_at_cursor:
        #     block_name = self.block_at_cursor.get("displayName", self.block_at_cursor.get("name", "未知方块"))
        #     block_pos = self.block_at_cursor.get("position", {})
        #     if block_pos:
        #         lines.append(f"  光标指向: {block_name} 在 ({block_pos.get('x', 0)}, {block_pos.get('y', 0)}, {block_pos.get('z', 0)})")
        
        # if self.entity_at_cursor:
        #     entity_name = self.entity_at_cursor.get("displayName", self.entity_at_cursor.get("name", "未知实体"))
        #     lines.append(f"  光标指向实体: {entity_name}")
        
        # 装备信息
        if self.equipment:
            equipped_items = []
            for slot, item in self.equipment.items():
                if item:
                    item_name = item.get("displayName", item.get("name", "未知物品"))
                    equipped_items.append(f"{slot}: {item_name}")
            if equipped_items:
                lines.append(f"  装备: {', '.join(equipped_items)}")
        
        lines.append("")
        
        # 物品栏
        lines.append("【物品栏】")
        if self.inventory:
            if self.empty_slot_count == 0:
                lines.append("物品栏已满！无法装入新物品！")
            else:
                lines.append(f"物品栏有{self.empty_slot_count}个空槽位")
            # 按槽位排序显示物品
            sorted_inventory = sorted(self.inventory, key=lambda x: x.get('slot', 0) if isinstance(x, dict) else 0)
            
            for item in sorted_inventory:
                # 构建更可读的物品信息
                item_info = []
                
                # 添加类型检查，确保item是字典类型
                if isinstance(item, dict):
                    if 'name' in item and item['name']:
                        item_info.append(item['name'])
                    if 'count' in item and item['count'] > 0:
                        item_info.append(f"x{item['count']} ")
                elif isinstance(item, str):
                    # 如果item是字符串，直接显示
                    item_info.append(item)
                else:
                    # 其他类型，转换为字符串显示
                    item_info.append(str(item))
                
                # 组合物品信息
                item_str = " ".join(item_info)
                lines.append(f"  {item_str}")
        else:
            lines.append("  物品栏为空")
        lines.append("")
        
        # 附近玩家
        lines.append("【附近玩家】")
        if self.nearby_players:
            lines.append(f"  附近玩家数量: {len(self.nearby_players)}")
            for i, player in enumerate(self.nearby_players, 1):
                lines.append(f"  {i}. {player.display_name} ({player.username})")
                lines.append(f"     延迟: {player.ping}ms, 游戏模式: {player.gamemode}")
        else:
            lines.append("  附近没有其他玩家")
        lines.append("")
        
        # 附近实体
        lines.append("【附近实体】")
        if self.nearby_entities:
            lines.append(f"  附近实体数量: {len(self.nearby_entities)}")
            for i, entity in enumerate(self.nearby_entities, 1):
                pos = entity.position
                lines.append(f"  {i}. {entity.name} (ID: {entity.id}, 类型: {entity.type})")
                lines.append(f"     位置: X={pos.x:.2f}, Y={pos.y:.2f}, Z={pos.z:.2f}")
        lines.append("")
        
        
        if self.overview_str:
            lines.append("【周围环境鸟瞰】")
            lines.append(self.overview_str)
            lines.append("")
        
        # 最近事件
        lines.append("【最近事件】")
        if self.recent_events:
            # 限制显示最近的事件数量，避免信息过多
            max_events = 10
            recent_events_to_show = self.recent_events[-max_events:] if len(self.recent_events) > max_events else self.recent_events
            
            for i, event in enumerate(recent_events_to_show, 1):
                event_desc = self._get_event_description(event)
                # 添加格式化的时间戳信息
                if event:
                    timestamp_str = ""
                    if event.timestamp:
                        try:
                            dt = datetime.fromtimestamp(event.timestamp)
                            timestamp_str = f"[{dt.strftime('%H:%M:%S')}]"
                        except (ValueError, OSError):
                            # 如果时间戳转换失败，使用原始时间戳
                            timestamp_str = f"[{event.timestamp:.1f}s]"
                    lines.append(f"  {i}. {timestamp_str} {event_desc}")
        else:
            lines.append("  暂无最近事件记录")
        lines.append("")
        
        lines.append("=" * 10)
        
        return "\n".join(lines)
    
    def get_chat_str(self) -> str:
        """获取所有聊天事件的字符串表示"""
        lines = ["【聊天记录】"]
        
        if not self.recent_events:
            lines.append("暂无聊天记录")
            return "\n".join(lines)
        
        # 筛选出聊天事件
        chat_events = [event for event in self.recent_events if event.type == "chat"]
        
        if not chat_events:
            lines.append("暂无聊天记录")
            return "\n".join(lines)
        
        # 按时间戳排序（从旧到新）
        sorted_chat_events = sorted(chat_events, key=lambda x: x.timestamp)
        
        # 限制显示的聊天数量，避免信息过多
        max_chats = 30
        chats_to_show = sorted_chat_events[-max_chats:] if len(sorted_chat_events) > max_chats else sorted_chat_events
        
        lines.append(f"最近 {len(chats_to_show)} 条聊天记录 (总计: {len(chat_events)} 条):")
        lines.append("")
        
        # 重新编号，确保最新的聊天记录在最下方且编号连续
        for i, event in enumerate(chats_to_show, 1):
            # 格式化时间戳
            timestamp_str = ""
            if event.timestamp:
                try:
                    # 尝试将gameTick转换为可读时间
                    # 假设1秒 = 20 ticks
                    total_seconds = event.timestamp / 20
                    minutes = int(total_seconds // 60)
                    seconds = int(total_seconds % 60)
                    
                    # 对于Minecraft的gameTick，直接显示时间，不限制分钟数
                    timestamp_str = f"[{minutes:02d}:{seconds:02d}]"
                    
                except (ValueError, OSError):
                    # 如果转换失败，使用原始时间戳
                    timestamp_str = f"[{event.timestamp}ticks]"
            
            # 获取聊天内容
            chat_content = ""
            if hasattr(event, 'chat_text') and event.chat_text:
                chat_content = event.chat_text
            else:
                chat_content = "未知内容"
            
            # 获取玩家名称
            player_name = event.player_name or "未知玩家"
            
            # 构建聊天行
            chat_line = f"  {i}. {timestamp_str} {player_name}: {chat_content}"
            lines.append(chat_line)
        
        lines.append("")
        lines.append("=" * 10)
        
        return "\n".join(lines)
    
    
    def _get_event_description(self, event: Event) -> str:
        """获取事件描述"""
        
        # logger.info(f"事件: {event}")
        
        # 获取玩家名称，优先使用事件中的玩家名称
        player_name = event.player_name or "未知玩家"
        base_desc = f"{event.type} - {player_name}"
        
        # 根据事件类型生成详细描述
        if event.type == "playerMove" and event.old_position and event.new_position:
            old_pos = event.old_position
            new_pos = event.new_position
            return f"{base_desc} 从 ({old_pos.x:.1f}, {old_pos.y:.1f}, {old_pos.z:.1f}) 移动到 ({new_pos.x:.1f}, {new_pos.y:.1f}, {new_pos.z:.1f})"
        
        elif event.type == "blockBreak" and event.block:
            block = event.block
            pos = block.position
            return f"{base_desc} 破坏了 {block.name} 在 ({pos.x:.1f}, {pos.y:.1f}, {pos.z:.1f})"
        
        elif event.type == "blockPlace" and event.block:
            block = event.block
            pos = block.position
            return f"{base_desc} 放置了 {block.name} 在 ({pos.x:.1f}, {pos.y:.1f}, {pos.z:.1f})"
        
        elif event.type == "experienceUpdate":
            return f"{base_desc} 经验值更新: {event.experience}, 等级: {event.level}"
        
        elif event.type == "healthUpdate":
            health_info = f"生命值: {event.health}"
            food_info = f"饥饿值: {event.food}"
            saturation_info = f"饱和度: {event.saturation}" if event.saturation is not None else ""
            
            info_parts = [health_info, food_info]
            if saturation_info:
                info_parts.append(saturation_info)
            
            return f"{base_desc} 状态更新: {', '.join(info_parts)}"
        
        elif event.type == "playerJoin":
            return f"{base_desc} 加入了游戏"
        
        elif event.type == "playerLeave":
            return f"{base_desc} 离开了游戏"
        
        elif event.type == "playerDeath":
            return f"{base_desc} 死亡了"
        
        elif event.type == "playerRespawn":
            if event.new_position:
                pos = event.new_position
                return f"{base_desc} 重生于 ({pos.x:.1f}, {pos.y:.1f}, {pos.z:.1f})"
            else:
                return f"{base_desc} 重生了"
        
        elif event.type == "playerKick":
            if hasattr(event, 'kick_reason') and event.kick_reason:
                return f"{base_desc} 被踢出游戏: {event.kick_reason}"
            else:
                return f"{base_desc} 被踢出游戏"
        
        elif event.type == "entityHurt":
            if hasattr(event, 'entity_name') and event.entity_name:
                entity_name = event.entity_name
                if hasattr(event, 'damage') and event.damage is not None:
                    return f"{base_desc} 对 {entity_name} 造成了 {event.damage} 点伤害"
                else:
                    return f"{base_desc} 攻击了 {entity_name}"
            else:
                return f"{base_desc} 攻击了实体"
        
        elif event.type == "entityDeath":
            if hasattr(event, 'entity_name') and event.entity_name:
                entity_name = event.entity_name
                if hasattr(event, 'entity_position') and event.entity_position:
                    pos = event.entity_position
                    return f"{base_desc} 击杀了 {entity_name} 在 ({pos.x:.1f}, {pos.y:.1f}, {pos.z:.1f})"
                else:
                    return f"{base_desc} 击杀了 {entity_name}"
            else:
                return f"{base_desc} 击杀了实体"
        
        elif event.type == "weatherChange":
            if hasattr(event, 'weather') and event.weather:
                return f"{base_desc} 天气变为: {event.weather}"
            else:
                return f"{base_desc} 天气发生了变化"
        
        elif event.type == "spawnPointReset":
            return f"{base_desc} 重置了出生点"
        
        else:
            return ""

    @staticmethod
    def compare_inventories(old_inventory: List[Dict[str, Any]], new_inventory: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        比较两个inventory的差异
        
        Args:
            old_inventory: 旧的物品栏列表
            new_inventory: 新的物品栏列表
            
        Returns:
            包含差异信息的字典:
            {
                'added': [{'name': '物品名', 'count': 数量, 'slot': 槽位}],
                'removed': [{'name': '物品名', 'count': 数量, 'slot': 槽位}],
                'changed': [{'name': '物品名', 'old_count': 旧数量, 'new_count': 新数量, 'slot': 槽位}],
                'summary': '差异摘要文本'
            }
        """
        # 创建物品名称到物品信息的映射，用于快速查找
        old_items = {}
        new_items = {}
        
        # 处理旧物品栏
        for item in old_inventory:
            if isinstance(item, dict) and 'name' in item and item['name']:
                item_name = item['name']
                if item_name not in old_items:
                    old_items[item_name] = []
                old_items[item_name].append({
                    'name': item_name,
                    'count': item.get('count', 0),
                    'slot': item.get('slot', 0)
                })
        
        # 处理新物品栏
        for item in new_inventory:
            if isinstance(item, dict) and 'name' in item and item['name']:
                item_name = item['name']
                if item_name not in new_items:
                    new_items[item_name] = []
                new_items[item_name].append({
                    'name': item_name,
                    'count': item.get('count', 0),
                    'slot': item.get('slot', 0)
                })
        
        added = []
        removed = []
        changed = []
        
        # 检查新增的物品
        for item_name, new_item_list in new_items.items():
            if item_name not in old_items:
                # 完全新增的物品
                for new_item in new_item_list:
                    added.append(new_item.copy())
            else:
                # 检查数量变化
                old_item_list = old_items[item_name]
                
                # 简单的数量比较（假设相同名称的物品数量变化）
                old_total_count = sum(item['count'] for item in old_item_list)
                new_total_count = sum(item['count'] for item in new_item_list)
                
                if new_total_count > old_total_count:
                    # 数量增加
                    added.append({
                        'name': item_name,
                        'count': new_total_count - old_total_count,
                        'slot': 'multiple'  # 多个槽位
                    })
                elif new_total_count < old_total_count:
                    # 数量减少
                    removed.append({
                        'name': item_name,
                        'count': old_total_count - new_total_count,
                        'slot': 'multiple'  # 多个槽位
                    })
                
                # 检查具体槽位的变化
                for new_item in new_item_list:
                    new_slot = new_item['slot']
                    new_count = new_item['count']
                    
                    # 查找相同槽位的旧物品
                    old_item_in_slot = None
                    for old_item in old_item_list:
                        if old_item['slot'] == new_slot:
                            old_item_in_slot = old_item
                            break
                    
                    if old_item_in_slot is None:
                        # 这个槽位新增了物品
                        added.append(new_item.copy())
                    elif old_item_in_slot['count'] != new_count:
                        # 这个槽位的物品数量发生了变化
                        changed.append({
                            'name': item_name,
                            'old_count': old_item_in_slot['count'],
                            'new_count': new_count,
                            'slot': new_slot
                        })
        
        # 检查移除的物品
        for item_name, old_item_list in old_items.items():
            if item_name not in new_items:
                # 完全移除的物品
                for old_item in old_item_list:
                    removed.append(old_item.copy())
            else:
                # 检查具体槽位的移除
                new_item_list = new_items[item_name]
                for old_item in old_item_list:
                    old_slot = old_item['slot']
                    
                    # 查找相同槽位的新物品
                    new_item_in_slot = None
                    for new_item in new_item_list:
                        if new_item['slot'] == old_slot:
                            new_item_in_slot = new_item
                            break
                    
                    if new_item_in_slot is None:
                        # 这个槽位的物品被移除了
                        removed.append(old_item.copy())
        
        # 生成摘要文本
        summary_parts = []
        if added:
            added_summary = ", ".join([f"{item['name']}x{item['count']}" for item in added])
            summary_parts.append(f"新增: {added_summary}")
        
        if removed:
            removed_summary = ", ".join([f"{item['name']}x{item['count']}" for item in removed])
            summary_parts.append(f"减少: {removed_summary}")
        
        if changed:
            changed_summary = ", ".join([f"{item['name']} {item['old_count']}→{item['new_count']}" for item in changed])
            summary_parts.append(f"变化: {changed_summary}")
        
        if not summary_parts:
            summary = "物品栏没有变化"
        else:
            summary = "; ".join(summary_parts)
        
        return {
            'added': added,
            'removed': removed,
            'changed': changed,
            'summary': summary
        }

    @staticmethod
    def get_inventory_diff_text(old_inventory: List[Dict[str, Any]], new_inventory: List[Dict[str, Any]]) -> str:
        """
        获取两个inventory差异的可读文本
        
        Args:
            old_inventory: 旧的物品栏列表
            new_inventory: 新的物品栏列表
            
        Returns:
            格式化的差异文本
        """
        diff = EnvironmentInfo.compare_inventories(old_inventory, new_inventory)
        
        lines = ["【物品栏变化】"]
        
        if diff['added']:
            lines.append("新增物品:")
            for item in diff['added']:
                slot_info = f" (槽位{item['slot']})" if item['slot'] != 'multiple' else ""
                lines.append(f"  + {item['name']} x{item['count']}{slot_info}")
        
        if diff['removed']:
            lines.append("减少物品:")
            for item in diff['removed']:
                slot_info = f" (槽位{item['slot']})" if item['slot'] != 'multiple' else ""
                lines.append(f"  - {item['name']} x{item['count']}{slot_info}")
        
        if diff['changed']:
            lines.append("数量变化:")
            for item in diff['changed']:
                lines.append(f"  {item['name']}: {item['old_count']} → {item['new_count']} (槽位{item['slot']})")
        
        if not any([diff['added'], diff['removed'], diff['changed']]):
            lines.append("物品栏没有变化")
        
        return "\n".join(lines)

    def get_held_item_info(self) -> str:
        """获取手持物品的详细信息"""
        if not self.held_item:
            return "没有手持物品"
        
        item_name = self.held_item.get("displayName", self.held_item.get("name", "未知物品"))
        item_count = self.held_item.get("count", 1)
        durability = self.held_item.get("maxDurability", 0)
        
        info_lines = [f"手持物品: {item_name} x{item_count}"]
        
        # 添加耐久度信息
        if durability > 1:
            current_damage = 0
            if self.held_item.get("components"):
                for component in self.held_item["components"]:
                    if component.get("type") == "damage":
                        current_damage = component.get("data", 0)
                        break
            
            remaining_durability = durability - current_damage
            info_lines.append(f"耐久度: {remaining_durability}/{durability}")
            
            # 添加耐久度百分比
            if durability > 0:
                durability_percent = (remaining_durability / durability) * 100
                info_lines.append(f"耐久度百分比: {durability_percent:.1f}%")
        
        # 添加物品类型信息
        if self.held_item.get("material"):
            info_lines.append(f"挖掘工具: {self.held_item['material']}")
        
        # 添加是否正在使用的状态
        if self.using_held_item:
            info_lines.append("状态: 正在使用中")
        
        return "\n".join(info_lines)

    def get_cursor_info(self) -> str:
        """获取光标指向的信息"""
        info_lines = ["【光标信息】"]
        
        if self.block_at_cursor:
            block_name = self.block_at_cursor.get("displayName", self.block_at_cursor.get("name", "未知方块"))
            block_pos = self.block_at_cursor.get("position", {})
            
            info_lines.append(f"指向方块: {block_name}")
            if block_pos:
                info_lines.append(f"位置: ({block_pos.get('x', 0)}, {block_pos.get('y', 0)}, {block_pos.get('z', 0)})")
            
            # 添加方块属性信息
            if self.block_at_cursor.get("hardness") is not None:
                info_lines.append(f"硬度: {self.block_at_cursor['hardness']}")
            
            if self.block_at_cursor.get("material"):
                info_lines.append(f"挖掘工具: {self.block_at_cursor['material']}")
            
            if self.block_at_cursor.get("transparent") is not None:
                info_lines.append(f"透明: {'是' if self.block_at_cursor['transparent'] else '否'}")
            
            if self.block_at_cursor.get("diggable") is not None:
                info_lines.append(f"可挖掘: {'是' if self.block_at_cursor['diggable'] else '否'}")
        
        if self.entity_at_cursor:
            entity_name = self.entity_at_cursor.get("displayName", self.entity_at_cursor.get("name", "未知实体"))
            info_lines.append(f"指向实体: {entity_name}")
            
            # 添加实体属性信息
            if self.entity_at_cursor.get("health") is not None:
                max_health = self.entity_at_cursor.get("maxHealth", 0)
                if max_health > 0:
                    info_lines.append(f"生命值: {self.entity_at_cursor['health']}/{max_health}")
                else:
                    info_lines.append(f"生命值: {self.entity_at_cursor['health']}")
        
        if not self.block_at_cursor and not self.entity_at_cursor:
            info_lines.append("光标没有指向任何方块或实体")
        
        return "\n".join(info_lines)

    def get_movement_info(self) -> str:
        """获取移动相关信息"""
        info_lines = ["【移动信息】"]
        
        if self.velocity:
            speed = (self.velocity.x**2 + self.velocity.y**2 + self.velocity.z**2)**0.5
            info_lines.append(f"当前速度: {speed:.2f} 方块/秒")
            info_lines.append(f"速度向量: X={self.velocity.x:.2f}, Y={self.velocity.y:.2f}, Z={self.velocity.z:.2f}")
        else:
            info_lines.append("当前速度: 静止")
        
        info_lines.append(f"是否在地面上: {'是' if self.on_ground else '否'}")
        info_lines.append(f"是否在睡觉: {'是' if self.is_sleeping else '否'}")
        
        if self.position:
            info_lines.append(f"当前位置: X={self.position.x:.2f}, Y={self.position.y:.2f}, Z={self.position.z:.2f}")
        
        return "\n".join(info_lines)


# 全局环境信息实例
global_environment = EnvironmentInfo()
