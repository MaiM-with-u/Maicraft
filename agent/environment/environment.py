"""
Minecraft环境信息存储类
用于存储和管理游戏环境数据
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from utils.logger import get_logger
from agent.common.basic_class import Player, Position, Entity, Event, BlockPosition
from agent.block_cache.block_cache import global_block_cache
from openai_client.llm_request import LLMClient
from agent.environment.locations import global_location_points
from config import global_config
from agent.thinking_log import global_thinking_log
from agent.mai_mode import mai_mode
from agent.block_cache.nearby_block import nearby_block_manager
from agent.to_do_list import mai_goal, mai_to_do_list
from agent.utils.utils import format_task_done_list
from agent.prompt_manager.prompt_manager import prompt_manager
from agent.container_cache.container_cache import global_container_cache
from openai_client.modelconfig import ModelConfig
from agent.chat_history import global_chat_history
from agent.environment.inventory_utils import review_all_tools
import traceback
from agent.common.basic_class import PlayerEntity, ItemEntity, AnimalEntity

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
        # self.nearby_players: List[Player] = []
        
        # 附近实体
        self.nearby_entities: List[Entity] = []
        
        
        # 最近事件
        self.recent_events: List[Event] = []
        
        
        # 时间戳
        self.last_update: Optional[datetime] = None
        
        
        model_config = ModelConfig(
                model_name=global_config.vlm.model,
                api_key=global_config.vlm.api_key,
                base_url=global_config.vlm.base_url,
                max_tokens=global_config.vlm.max_tokens,
                temperature=global_config.vlm.temperature
            )
            
        self.vlm = LLMClient(model_config)
        
    def add_event(self, event: Event):
        self.recent_events.append(event)
        if len(self.recent_events) > 80:
            self.recent_events = self.recent_events[80:]
        
    async def get_overview_str(self) -> str:
        if not self.vlm:
            return ""
        prompt = """
你是一个经验丰富的Minecraft玩家，现在你正在一个Minecraft世界中，请根据你看到的画面，描述你周围的环境。和关键坐标
        """
        
        logger.info(f"prompt: {prompt}")
        result = await self.vlm.simple_vision(prompt, self.overview_base64)
        logger.info(f"result: {result}")
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
        
        # logger.info(f"data: {data}")
        # 更新视角信息
        self.yaw = data.get("yaw")
        self.pitch = data.get("pitch")
        
        # logger.info(f"yaw: {self.yaw}, pitch: {self.pitch}")
        
        # 缓存玩家位置和视角信息到方块缓存系统
        if self.position and self.player_name:
            try:
                global_block_cache.update_player_position(
                    player_name=self.player_name,
                    position=self.position,
                    yaw=self.yaw,
                    pitch=self.pitch
                )
            except Exception as e:
                logger.warning(f"缓存玩家位置信息失败: {e}")
        
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
        
        # # 更新周围环境 - 玩家 (来自 query_surroundings("players"))
        # if "nearbyPlayers" in data:
        #     nearby_players_data = data["nearbyPlayers"]
        #     if isinstance(nearby_players_data, list):
        #         # 如果nearbyPlayers是列表，直接使用
        #         self.nearby_players = []
        #         for player_data in nearby_players_data:
        #             try:
        #                 if isinstance(player_data, dict):
        #                     player = Player(
        #                         uuid=player_data.get("uuid", ""),
        #                         username=player_data.get("username", ""),
        #                         display_name=player_data.get("displayName", ""),
        #                         ping=player_data.get("ping", 0),
        #                         gamemode=player_data.get("gamemode", 0)
        #                     )
        #                     self.nearby_players.append(player)
        #                 else:
        #                     # 如果只是玩家名称字符串
        #                     player = Player(
        #                         uuid="",
        #                         username=str(player_data),
        #                         display_name=str(player_data),
        #                         ping=0,
        #                         gamemode=0
        #                     )
        #                     self.nearby_players.append(player)
        #             except Exception as e:
        #                 # 记录玩家处理错误，但继续处理其他玩家
        #                 import traceback
        #                 print(f"处理玩家数据时出错: {e}")
        #                 print(f"玩家数据: {player_data}")
        #                 print(f"错误详情: {traceback.format_exc()}")
        #                 continue
        # 更新时间戳
        self.last_update = datetime.now()
        
    def update_nearby_entities(self, entities_list: List[Dict[str, Any]]):
        self.nearby_entities = []
        for entity_data in entities_list:
            # logger.info(entity_data)
            # 解析位置 [x, y, z]
            position = Position(0.0, 0.0, 0.0)
            pos_data = entity_data["position"]
            position = Position(
                x=float(pos_data[0]) if pos_data[0] is not None else 0.0,
                y=float(pos_data[1]) if pos_data[1] is not None else 0.0,
                z=float(pos_data[2]) if pos_data[2] is not None else 0.0
            )
            # 解析实体信息
            entity_type = entity_data.get("type", "other")
            entity_name = entity_data.get("name", "未知实体")
            
            # 特殊处理玩家实体
            if entity_type == "player":
                entity = PlayerEntity(
                    type=entity_type,
                    name=entity_name,
                    username= entity_data.get("username"),
                    position=position,
                    distance=(float(entity_data.get("distance")) if entity_data.get("distance") is not None else None),
                    health=(int(entity_data.get("health")) if entity_data.get("health") is not None else None),
                    max_health=(int(entity_data.get("maxHealth")) if entity_data.get("maxHealth") is not None else None)
                )
            # 特殊处理物品实体
            elif entity_type == "animal":
                entity = AnimalEntity(
                    type=entity_type,
                    name=entity_name,
                    position=position,
                    distance=(float(entity_data.get("distance")) if entity_data.get("distance") is not None else None),
                    health=(int(entity_data.get("health")) if entity_data.get("health") is not None else None),
                    max_health=(int(entity_data.get("maxHealth")) if entity_data.get("maxHealth") is not None else None)
                )
            else:
                if entity_name == "item":
                    item_info = entity_data.get("itemsInfo", [])[0]
                    item_name = item_info.get("name")
                    item_count = item_info.get("count", 1)
                    entity = ItemEntity(
                        type=entity_type,
                        name=entity_name,
                        item_name=item_name,
                        count=item_count,
                        position=position,
                    )
                else:
                    entity = Entity(
                        type=entity_type,
                        name=entity_name,
                        position=position,
                        distance=(float(entity_data.get("distance")) if entity_data.get("distance") is not None else None),
                        health=(int(entity_data.get("health")) if entity_data.get("health") is not None else None),
                        max_health=(int(entity_data.get("maxHealth")) if entity_data.get("maxHealth") is not None else None)
                    )

            self.nearby_entities.append(entity)
            
    def mob_nearby(self):
        for entity in self.nearby_entities:
            if entity.type == "player" or entity.type == "animal":
                return True
        return False
        
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
        position_str = f"""你现在的坐标(脚所在的坐标)是：x={self.block_position.x}, y={self.block_position.y}, z={self.block_position.z}
{block_on_feet_str}
        """
        
        location_list = global_location_points.all_location_str()
        
        is_on_ground_str = f"  是否在地面上: {self.on_ground}"
        
        final_str = f"""
{position_str}
{is_on_ground_str}
{location_list}
        """
        
        return final_str
    
    def get_self_info(self) -> str:
        lines = []
        
        # 玩家信息
        if self.player_name:
            lines.append(f"  用户名: {self.player_name}")
            lines.append(f"  游戏模式: {self.gamemode}")
            
        return "\n".join(lines)
            
    
    def get_equipment_info(self) -> str:
        lines = []
        if self.equipment:
            equipped_items = []
            for slot, item in self.equipment.items():
                if item:
                    item_name = item.get("name", "未知物品")
                    equipped_items.append(f"{slot}: {item_name}")
            if equipped_items:
                lines.append(f"  装备: {', '.join(equipped_items)}")
                lines.append(f"  护甲值: {self.armor}")
        return "\n".join(lines)
    
    def get_held_item_info(self) -> str:
        lines = []
        if self.held_item:
            item_name = self.held_item.get("name", "未知物品")
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
            
        return "\n".join(lines)
    
    def get_inventory_info(self) -> str:
        lines = []
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
                
            tool_tip_str = review_all_tools(self.inventory)
            lines.append(tool_tip_str)
                
        else:
            lines.append("  物品栏为空")
        lines.append("")
        return "\n".join(lines)
    
    def get_nearby_entities_info(self) -> str:
        lines = []
        # if self.nearby_players:
        #     lines.append("附近玩家:")
        #     for i, player in enumerate(self.nearby_players, 1):
        #         lines.append(f"  {i}. {player.display_name} ({player.username})")
        #         # lines.append(f"     延迟: {player.ping}ms, 游戏模式: {player.gamemode}")
        
        if self.nearby_entities:
            # logger.info(f"附近实体: {self.nearby_entities}")
            lines.append(f" 附近实体数量: {len(self.nearby_entities)}")
            for i, entity in enumerate(self.nearby_entities, 1):
                # 物品实体显示名称和坐标
                lines.append(f"  {i}. {entity.__str__()}")
                
        return "\n".join(lines)
    
    def get_self_status_info(self) -> str:
        lines = []
        lines.append(f"  生命值: {self.health}/{self.health_max}")
        
        if self.food/self.food_max < 0.5:
            lines.append(f"  饥饿值: {self.food}/{self.food_max}，饥饿值较低，需要马上食用食物")
        elif self.food/self.food_max < 0.8:
            lines.append(f"  饥饿值: {self.food}/{self.food_max}，有条件最好食用食物")
        else:
            lines.append(f"  饥饿值: {self.food}/{self.food_max}")
            
        lines.append(f"  等级: {self.level}")
        return "\n".join(lines)

    def get_visual_info(self) -> str:
        """以可读文本形式返回所有环境信息"""
        lines = []
        if self.overview_str:
            lines.append("【周围环境鸟瞰】")
            lines.append(self.overview_str)
            lines.append("")
        
        lines.append("=" * 10)
        
        return "\n".join(lines)
    
    
    def get_chat_str(self) -> str:
        """获取所有聊天事件的字符串表示"""
        lines = []
        
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
        
        # lines.append(f"最近 {len(chats_to_show)} 条聊天记录 (总计: {len(chat_events)} 条):")
        
        # 重新编号，确保最新的聊天记录在最下方且编号连续
        for i, event in enumerate(chats_to_show, 1):
            # 格式化时间戳
            timestamp_str = ""
            if event.timestamp:
                from datetime import datetime
                try:
                    dt = datetime.fromtimestamp(event.timestamp)
                    timestamp_str = f"[{dt.strftime('%H:%M:%S')}]"
                except (ValueError, OSError):
                    timestamp_str = f"[{event.timestamp:.1f}s]"
            
            # 获取聊天内容
            chat_content = ""
            if event.chat_text:
                chat_content = event.chat_text
            else:
                chat_content = "未知内容"
            
            # 获取玩家名称
            player_name = event.player_name or "未知玩家"
            
            # 构建聊天行
            # chat_line = f"  {i}. {timestamp_str} {player_name}: {chat_content}"
            chat_line = f"{timestamp_str}{player_name}: {chat_content}"
            lines.append(chat_line)
        
        return "\n".join(lines)
    

    
    async def get_all_data(self) -> dict:
        if self.food/self.food_max < 0.8:
            eat_action = """**eat**
食用某样物品回复饱食度
食用背包中的物品。
如果背包中没有食物，可以尝试找寻苹果，或寻找附近的动物以获得食物
{
    "action_type":"eat",
    "item":"食物名称",
}"""
        else:
            eat_action = ""
            
            
        if self.mob_nearby():
            kill_mob_action = """**kill_mob**
杀死某个实体
杀死动物，怪物或玩家
{{
    "action_type":"kill_mob",
    "entity":"需要杀死的实体名称",
    "timeout":"杀死实体的超时时间，单位：秒",
}}"""
        else:
            kill_mob_action = ""
        
        
        input_data = {
            "self_info": self.get_self_info(),
            "basic_info": "",
            "task": "当前没有选择明确的任务",
            "visual_info": self.get_visual_info(),
            "inventory_info": self.get_inventory_info(),
            "full_thinking_list": global_thinking_log.get_thinking_log_full(),
            "thinking_list": global_thinking_log.get_thinking_log(),
            "nearby_block_info": await nearby_block_manager.get_visible_blocks_str(self.block_position,distance=16),
            "position": self.get_position_str(),
            "chat_str": global_chat_history.get_chat_history_str(),
            "to_do_list": mai_to_do_list.__str__(),
            "task_done_list": format_task_done_list(),
            "goal": mai_goal.goal,
            "mode": mai_mode.mode,
            "eat_action": eat_action,
            "kill_mob_action": kill_mob_action,
            "nearby_entities_info": self.get_nearby_entities_info(),
            "failed_hint": "",
            "judge_guidance": global_thinking_log.judge_guidance,
            "self_status_info": self.get_self_status_info(),
        }
        
        # 添加容器缓存信息
        container_cache_info = ""
        if self.block_position:
            nearby_containers_info = global_container_cache.get_nearby_containers_info(self.block_position, 3)
            container_cache_info += nearby_containers_info
        input_data["container_cache_info"] = container_cache_info
        
        basic_info = prompt_manager.generate_prompt("basic_info", **input_data)
        input_data["basic_info"] = basic_info
        
        
        return input_data


# 全局环境信息实例
global_environment = EnvironmentInfo()
