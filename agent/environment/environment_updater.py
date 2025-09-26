"""
环境信息更新器
使用新的拆分后的查询工具来更新Minecraft环境信息
"""

import asyncio
import time
import traceback
from types import CoroutineType
from typing import Optional, Dict, Any, Set
from datetime import datetime
from utils.logger import get_logger
from agent.environment.environment import global_environment
import json
from agent.block_cache.block_cache import global_block_cache
from agent.common.basic_class import Player, BlockPosition
from agent.events import EventFactory, EventType, global_event_store, global_event_emitter
from agent.thinking_log import global_thinking_log
from mcp_server.client import global_mcp_client
from agent.chat_history import global_chat_history
from utils.logger import get_logger

logger = get_logger("EnvironmentUpdater")   
class EnvironmentUpdater:
    """环境信息定期更新器"""
    
    def __init__(self,update_interval: int = 0.1):
        """
        初始化环境更新器

        Args:
            agent: MaicraftAgent实例，用于调用查询工具
            update_interval: 更新间隔（秒），默认3秒
            auto_start: 是否自动开始更新，默认False
        """
        self.update_interval = update_interval
        self.logger = get_logger("EnvironmentUpdater")

        # 更新状态
        self.is_running = False
        self.is_paused = False

        # 异步任务控制
        self._update_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._pause_event = asyncio.Event()

        # 统计信息
        self.update_count = 0
        self.last_update_time: Optional[datetime] = None
        self.last_update_duration = 0.0
        self.average_update_duration = 0.0
        self.total_update_duration = 0.0

        # 事件处理相关
        self.last_processed_tick: int = 0  # 记录最后处理的事件 gameTick

        # 威胁处理状态跟踪 - 避免反复中断攻击决策
        self.in_threat_alert_mode = False  # 是否处于威胁警戒状态
        self.threat_count = 0  # 当前威胁数量
        
    
    def start(self) -> bool:
        """启动环境更新器"""
        if self.is_running:
            self.logger.warning("[EnvironmentUpdater] 更新器已在运行中")
            return False
        
        try:
            self._stop_event.clear()
            self._pause_event.clear()
            self.is_running = True
            self.is_paused = False
            
            # 使用asyncio.create_task启动异步更新循环
            try:
                # 如果已有事件循环，直接创建任务
                self._update_task = asyncio.create_task(self._update_loop())
                self.logger.info(f"[EnvironmentUpdater] 在现有事件循环中启动成功，更新间隔: {self.update_interval}秒")
            except RuntimeError:
                # 如果没有运行中的事件循环，记录错误
                self.logger.error("[EnvironmentUpdater] 无法获取运行中的事件循环")
                self.is_running = False
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"[EnvironmentUpdater] 启动失败: {e}")
            self.is_running = False
            return False
    
    
    async def _update_loop(self):
        """更新循环的主逻辑（异步版本）"""
        self.logger.info(f"[EnvironmentUpdater] 异步更新循环已启动，间隔: {self.update_interval}秒")
        
        while not self._stop_event.is_set():
            try:
                # 检查是否暂停
                if self._pause_event.is_set():
                    await asyncio.sleep(0.1)  # 暂停时短暂休眠
                    continue
                
                await self.perform_update()
                
                # 等待下次更新
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"[EnvironmentUpdater] 更新循环异常: {e}")
                await asyncio.sleep(1)  # 出错时等待1秒再继续
    
    
    async def perform_update(self):
        """执行单次环境更新（异步版本）"""
        try:
            
            
            # 使用新的拆分后的查询工具获取环境数据
            environment_data = await self._gather_environment_data()
            global_environment.update_from_observation(environment_data)
            
            await self.update_nearbyentities()
            await self.update_events()
            
            #更新周围方块
            if global_environment.block_position:
                await self._update_area_blocks_with_can_see(center_pos=global_environment.block_position, size=12)
                # self.logger.debug(f"[EnvironmentUpdater] 已更新 {can_see_updated_count} 个方块的 can_see 信息")
            
            
            
        except Exception as e:
            self.logger.error(f"[EnvironmentUpdater] 环境更新失败: {e}")
            await asyncio.sleep(1)
            self.logger.error(traceback.format_exc())

    async def update_nearbyentities(self):
        self.logger.debug("[环境更新] 开始更新附近实体信息")

        # 处理周围环境 - 实体
        results = await self._call_tool("query_surroundings", {"type": "entities","range":16,"useAbsoluteCoords":True})
        nearby_entities = results.get("data", {}).get("entities", {}).get("list", [])

        self.logger.debug(f"[环境更新] 获取到附近实体数量: {len(nearby_entities) if nearby_entities else 0}")

        # 统计不同类型的实体
        hostile_count = sum(1 for entity in nearby_entities if isinstance(entity, dict) and entity.get("type") == "hostile")
        self.logger.debug(f"[环境更新] 其中敌对生物数量: {hostile_count}")

        global_environment.update_nearby_entities(nearby_entities)
        self.logger.debug("[环境更新] 已更新全局环境实体信息")

        # 直接检测并攻击威胁生物
        self.logger.debug("[环境更新] 开始检查威胁生物并执行攻击")
        await self._check_and_attack_threats(nearby_entities)

    async def _check_and_attack_threats(self, nearby_entities):
        """直接检测并攻击威胁生物"""
        try:
            from config import global_config
            from agent.thinking_log import global_thinking_log
            from agent.environment.movement import global_movement
            from mcp_server.client import global_mcp_client
            from agent.utils.utils import parse_tool_result
            from agent.mai_agent import global_mai_agent

            self.logger.debug("[威胁检测] 开始检查")

            # 检查是否启用威胁生物检测
            if not global_config.threat_detection.enable_threat_detection:
                self.logger.debug("[威胁检测] 威胁生物检测已禁用")
                return

            detection_range = global_config.threat_detection.threat_detection_range
            self.logger.debug(f"[威胁检测] 检测范围: {detection_range}")

            # 过滤出需要攻击的生物
            hostile_mobs = []
            current_threat_count = 0
            if global_environment.position:
                for entity_dict in nearby_entities:
                    if isinstance(entity_dict, dict) and self._is_hostile_entity(entity_dict):
                        # 转换为Entity对象
                        entity = self._create_entity_from_dict(entity_dict)
                        if entity and entity.position:
                            distance = global_environment.position.distanceTo(entity.position)
                            if distance <= detection_range:
                                hostile_mobs.append((entity, distance))
                                current_threat_count += 1

            self.logger.debug(f"[威胁检测] 检测到 {len(hostile_mobs)} 个需要攻击的生物在范围内")
            if hostile_mobs:
                # 记录威胁生物的详细信息
                for entity, distance in hostile_mobs:
                    self.logger.info(f"[威胁检测] 🔍 威胁生物: {entity.name} 距离: {distance:.2f} 位置: ({entity.position.x:.1f}, {entity.position.y:.1f}, {entity.position.z:.1f})")
            self.logger.debug(f"[威胁检测] 警戒状态: {self.in_threat_alert_mode}, 当前威胁数量: {self.threat_count}")

            # 威胁警戒状态管理
            should_trigger_interrupt = False

            if hostile_mobs:
                # 有需要攻击的生物存在
                if not self.in_threat_alert_mode:
                    # 不在警戒状态，检测到新威胁 → 进入警戒状态并触发中断
                    self.logger.info(f"[威胁检测] 🔴 检测到新威胁！进入威胁警戒状态")
                    self.in_threat_alert_mode = True
                    self.threat_count = current_threat_count
                    should_trigger_interrupt = True
                else:
                    # 已在警戒状态，更新威胁数量
                    self.logger.debug(f"[威胁检测] 🟡 已在警戒状态，继续监控威胁")
                    self.threat_count = current_threat_count
            else:
                # 没有需要攻击的生物
                if self.in_threat_alert_mode:
                    # 在警戒状态但没有威胁了 → 退出警戒状态
                    self.logger.info(f"[威胁检测] 🟢 威胁已清除，退出威胁警戒状态")
                    self.in_threat_alert_mode = False
                    self.threat_count = 0
                    # 切换回主模式
                    from agent.mai_mode import mai_mode
                    mai_mode.mode = "main_mode"
                    self.logger.info("[威胁检测] 🟢 已切换回主模式，恢复LLM决策")
                else:
                    # 不在警戒状态且没有威胁，正常状态
                    self.logger.debug(f"[威胁检测] 🟢 周围安全，无威胁")

            # 添加威胁状态超时重置机制（防止卡死）
            if self.in_threat_alert_mode:
                # 记录威胁开始时间（如果还没记录）
                if not hasattr(self, 'threat_start_time'):
                    self.threat_start_time = time.time()
                
                # 如果威胁状态持续超过5分钟，强制重置
                if time.time() - self.threat_start_time > 300:  # 5分钟
                    self.logger.warning(f"[威胁检测] ⏰ 威胁状态持续超过5分钟，强制重置")
                    self.reset_threat_alert_mode()
                    if hasattr(self, 'threat_start_time'):
                        delattr(self, 'threat_start_time')
            else:
                # 清除威胁开始时间
                if hasattr(self, 'threat_start_time'):
                    delattr(self, 'threat_start_time')

            # 执行攻击逻辑（在警戒状态下持续攻击）
            if hostile_mobs and self.in_threat_alert_mode:
                self.logger.debug(f"[威胁检测] 🟡 警戒状态下攻击 {len(hostile_mobs)} 个敌对生物")

                # 按距离排序，优先攻击最近的
                hostile_mobs.sort(key=lambda x: x[1])

                for mob, distance in hostile_mobs:
                    mob_name = getattr(mob, 'name', '威胁生物')

                    self.logger.debug(f"[威胁检测] 攻击: {mob_name} 距离:{distance:.1f}")

                    try:
                        # 调用kill_mob工具
                        args = {"mob": mob_name}
                        call_result = await global_mcp_client.call_tool_directly("kill_mob", args)

                        # 解析工具调用结果
                        is_success, result_content = parse_tool_result(call_result)

                        if is_success:
                            self.logger.debug(f"[威胁检测] ✅ 成功攻击 {mob_name}")
                        else:
                            self.logger.debug(f"[威胁检测] ⚠️ 攻击 {mob_name} 失败: {result_content}")

                    except Exception as e:
                        self.logger.error(f"[威胁检测] 攻击 {mob_name} 时发生错误: {e}")

            # 中断逻辑只在进入警戒状态时触发一次
            if should_trigger_interrupt:
                # 按距离排序，优先显示最近的
                hostile_mobs.sort(key=lambda x: x[1])

                # 触发中断（与移动和AI决策）
                mob_names = [f"{mob.name}" for mob, _ in hostile_mobs[:3]]
                if len(hostile_mobs) > 3:
                    mob_names.append(f"等{len(hostile_mobs)}个")

                mob_list = ", ".join(mob_names)
                reason = f"⚔️ 检测到威胁生物！{mob_list} 已进入攻击范围，优先处理威胁！"

                self.logger.info(f"[威胁检测] 🔴 触发中断并激活警戒状态: {reason}")

                # 记录到思考日志
                global_thinking_log.add_thinking_log(
                    f"⚔️ 敌对生物威胁！{mob_list} 进入范围，激活威胁警戒模式！",
                    type="hostile_mob_alert_activated",
                )

                # 触发移动中断
                global_movement.trigger_interrupt(reason)

                # 触发AI决策中断并切换到威胁警戒模式
                if global_mai_agent:
                    global_mai_agent.trigger_interrupt(reason)
                    # 切换到威胁警戒模式 - 停止LLM决策，完全由程序控制
                    from agent.mai_mode import mai_mode
                    mai_mode.mode = "threat_alert_mode"
                    self.logger.info("[威胁检测] 🔴 已切换到威胁警戒模式，停止LLM决策")

        except Exception as e:
            self.logger.error(f"[威胁检测] 检测和攻击过程中出错: {e}")
            import traceback
            self.logger.error(f"[威胁检测] 异常详情: {traceback.format_exc()}")

    def reset_threat_alert_mode(self):
        """重置威胁警戒状态 - 用于外部干预或状态清理"""
        if self.in_threat_alert_mode or self.threat_count > 0:
            self.logger.info("[威胁检测] 外部重置威胁警戒状态")
            self.in_threat_alert_mode = False
            self.threat_count = 0
            # 切换回主模式
            from agent.mai_mode import mai_mode
            mai_mode.mode = "main_mode"
            self.logger.info("[威胁检测] 已切换回主模式，恢复LLM决策")

    def get_threat_handling_status(self) -> dict:
        """获取威胁处理状态"""
        return {
            "in_threat_alert_mode": self.in_threat_alert_mode,
            "threat_count": self.threat_count
        }

    def _is_hostile_entity(self, entity_dict: dict) -> bool:
        """判断实体是否是需要攻击的类型"""
        entity_type = entity_dict.get("type", "")
        entity_name = entity_dict.get("name", "").lower()

        # 需要攻击的实体类型
        hostile_types = {
            "hostile",  # 敌对生物
            "mob"       # 某些中性生物，如slime
        }

        # 需要攻击的特定生物名称（即使类型不是hostile）
        hostile_names = {
            "slime",
            "magma_cube",
            "ghast",
            "blaze",
            "wither_skeleton",
            "stray",
            "husk",
            "drowned",
            "phantom",
            "guardian",
            "elder_guardian",
            "shulker",
            "vex",
            "vindicator",
            "evoker",
            "pillager",
            "ravager"
        }

        # 检查类型或名称
        return entity_type in hostile_types or entity_name in hostile_names

    def _create_entity_from_dict(self, entity_data: dict):
        """从字典创建Entity对象"""
        try:
            from agent.common.basic_class import Position, Entity

            # 解析位置 [x, y, z]
            pos_data = entity_data.get("position")
            if not pos_data:
                return None

            position = Position(
                x=float(pos_data[0]) if pos_data[0] is not None else 0.0,
                y=float(pos_data[1]) if pos_data[1] is not None else 0.0,
                z=float(pos_data[2]) if pos_data[2] is not None else 0.0
            )

            # 解析实体信息
            entity_type = entity_data.get("type", "other")
            entity_name = entity_data.get("name", "未知实体")

            # 创建基础Entity对象
            entity = Entity(
                type=entity_type,
                name=entity_name,
                position=position,
                distance=(float(entity_data.get("distance")) if entity_data.get("distance") is not None else None),
                health=(int(entity_data.get("health")) if entity_data.get("health") is not None else None),
                max_health=(int(entity_data.get("maxHealth")) if entity_data.get("maxHealth") is not None else None)
            )

            # 设置实体ID（如果有的话）
            if "id" in entity_data:
                entity.id = entity_data["id"]

            return entity

        except Exception as e:
            self.logger.error(f"创建Entity对象时出错: {e}")
            return None

    async def update_events(self):
        """更新事件数据到环境信息中"""
        event_data = await self._call_tool("query_recent_events", {"sinceTick": self.last_processed_tick})
        recent_events = event_data.get("data", {})
        new_events = recent_events.get("events", [])
        
        # 更新 last_processed_tick 为最新的事件 tick
        if new_events:
            # 找到最大的 gameTick 值
            max_tick = max(event.get("gameTick", 0) for event in new_events if event.get("gameTick") is not None)
            # 每次获取后都更新 last_processed_tick 为最新事件的 gameTick
            self.last_processed_tick = max_tick + 1
            
            for event_data_item in new_events:
                try:
                    # 使用EventFactory从原始数据创建事件对象
                    event = EventFactory.from_raw_data(event_data_item)

                    # logger.info(event_data_item)

                    # 注意：entityHurt事件现在被启用用于伤害响应处理
                    ignore_event_name = []  # 不再忽略entityHurt事件
                    if event.type in ignore_event_name:
                        continue

                    # 使用统一的事件存储
                    global_event_store.add_event(event)

                    # ⭐ 新增：分发事件给所有监听器
                    await global_event_emitter.emit(event)

                    # 保留：向后兼容的硬编码处理
                    if event.type == EventType.CHAT.value:
                        global_chat_history.add_chat_history(event)


                except Exception as e:
                    self.logger.error(f"[EnvironmentUpdater] 处理事件失败: {e}")
                    self.logger.error(f"事件数据: {event_data_item}")
                    continue

                    
                    
    async def _gather_environment_data(self) -> Optional[Dict[str, Any]]:
        """使用新的查询工具收集环境数据"""
        try:
            # 并行调用所有查询工具
            tasks: list[CoroutineType[Any, Any, Dict[str, Any] | None]] = [
                self._call_tool("query_game_state", {}),
                self._call_tool("query_player_status", {"includeInventory":True}),
                self._call_tool("query_surroundings", {"type": "players","range":16,"useAbsoluteCoords":True}),
            ]
            
            # 等待所有查询完成
            results: list[Dict[str, Any] | BaseException | None] = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 记录每个查询工具的结果类型，用于调试
            for i, result in enumerate[Dict[str, Any] | BaseException | None](results):
                if isinstance(result, Exception):
                    self.logger.warning(f"[EnvironmentUpdater] 查询工具 {i} 返回异常: {result}")
            
            # 合并结果
            combined_data: dict[str, Any] = {
                "ok": True,
                "data": {},
                "request_id": "",
                "elapsed_ms": 0
            }
            
            # 处理游戏状态
            if isinstance(results[0], dict) and results[0].get("ok"):
                try:
                    game_state = results[0].get("data", {})
                    combined_data["data"].update(game_state)
                    combined_data["request_id"] = results[0].get("request_id", "")
                    combined_data["elapsed_ms"] = max(combined_data["elapsed_ms"], results[0].get("elapsed_ms", 0))
                except Exception as e:
                    self.logger.warning(f"[EnvironmentUpdater] 处理游戏状态数据时出错: {e}")
            
            # 处理玩家状态
            if isinstance(results[1], dict) and results[1].get("ok"):
                try:
                    player_status = results[1].get("data", {})
                    self.logger.debug(f"[EnvironmentUpdater] 原始玩家状态数据: {player_status}")

                    # 检查位置数据是否存在
                    if "position" in player_status:
                        self.logger.debug(f"[EnvironmentUpdater] 发现位置数据: {player_status['position']}")
                    else:
                        self.logger.warning("[EnvironmentUpdater] 玩家状态数据中未找到 position 字段")

                    # 新格式的玩家状态包含了更多信息，直接更新
                    combined_data["data"].update(player_status)
                    
                    # 处理物品栏信息（新格式中物品栏在player_status中）
                    if "inventory" in player_status:
                        combined_data["data"]["inventory"] = player_status["inventory"]
                    
                    # 处理光标信息
                    if "blockAtEntityCursor" in player_status:
                        combined_data["data"]["blockAtCursor"] = player_status["blockAtEntityCursor"]
                    if "entityAtCursor" in player_status:
                        combined_data["data"]["entityAtCursor"] = player_status["entityAtCursor"]
                    
                    # 处理手持物品信息
                    if "heldItem" in player_status:
                        combined_data["data"]["heldItem"] = player_status["heldItem"]
                    if "usingHeldItem" in player_status:
                        combined_data["data"]["usingHeldItem"] = player_status["usingHeldItem"]
                    
                    # 处理装备信息
                    if "equipment" in player_status:
                        combined_data["data"]["equipment"] = player_status["equipment"]
                    
                    # 处理其他新字段
                    for field in ["gamemode", "velocity", "armor", "isSleeping", "onGround", "yaw", "pitch", "biome"]:
                        if field in player_status:
                            combined_data["data"][field] = player_status[field]
                    
                    combined_data["elapsed_ms"] = max(combined_data["elapsed_ms"], results[1].get("elapsed_ms", 0))
                    self.logger.debug("[EnvironmentUpdater] 玩家状态数据更新成功")
                except Exception as e:
                    self.logger.warning(f"[EnvironmentUpdater] 处理玩家状态数据时出错: {e}")
                    self.logger.warning(traceback.format_exc())
            
            
            # 处理周围环境 - 玩家
            if isinstance(results[2], dict) and results[2].get("ok"):
                try:
                    nearby_players = results[2].get("data", {}).get("players", {})
                    if isinstance(nearby_players, dict) and "list" in nearby_players:
                        combined_data["data"]["nearbyPlayers"] = nearby_players.get("list", [])
                    else:
                        # 如果players不是预期的结构，设置为空列表
                        combined_data["data"]["nearbyPlayers"] = []
                    combined_data["elapsed_ms"] = max(combined_data["elapsed_ms"], results[2].get("elapsed_ms", 0))
                    self.logger.debug("[EnvironmentUpdater] 周围玩家数据更新成功")
                except Exception as e:
                    self.logger.warning(f"[EnvironmentUpdater] 处理周围玩家数据时出错: {e}")
                    combined_data["data"]["nearbyPlayers"] = []
            
            return combined_data
            
        except Exception as e:
            self.logger.error(f"[EnvironmentUpdater] 收集环境数据时发生异常: {e}")
            return None
        
    async def _call_tool(self, tool_name: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """调用工具"""
        try:
            result = await global_mcp_client.call_tool_directly(tool_name, params)
            if not result.is_error and result.content:
                content_text = result.content[0].text
                return json.loads(content_text)
            else:
                self.logger.error(f"[EnvironmentUpdater] {tool_name}调用失败: {result.content[0].text if result.content else 'Unknown error'}")
                return None
        except Exception as e:
            self.logger.error(f"[EnvironmentUpdater] 调用{tool_name}时发生异常: {e}")
            return None
    
    async def _update_area_blocks_with_can_see(self, center_pos: BlockPosition, size: int = 8) -> int:
        """更新区域方块数据，包括 can_see 信息
        
        Args:
            center_pos: 中心位置
            size: 区域大小（size x size）
            
        Returns:
            更新的方块数量
        """
        # 调用 query_area_blocks 工具
        # 计算区域边界
        half_size = size // 2
        start_x = center_pos.x - half_size
        start_y = center_pos.y - half_size
        start_z = center_pos.z - half_size
        end_x = center_pos.x + half_size
        end_y = center_pos.y + half_size
        end_z = center_pos.z + half_size
        
        # 调用工具
        result = await self._call_tool("query_area_blocks", {
            "startX": start_x,
            "startY": start_y,
            "startZ": start_z,
            "endX": end_x,
            "endY": end_y,
            "endZ": end_z,
            "useRelativeCoords": False,
            "maxBlocks": 10000,
            "compressionMode": False,
            "includeBlockCounts": False
        })
        
        
        if not result or not result.get("ok"):
            self.logger.warning("[EnvironmentUpdater] query_area_blocks 调用失败")
            return 0
        
        # logger.info(f"[EnvironmentUpdater] query_area_blocks 调用成功")
            
        try:
            data = result.get("data", {})
            # logger.info(f"[EnvironmentUpdater] query_area_blocks 调用成功: {data}")
            blocks = data.get("blocks", [])
            updated_count = 0
            
            # 创建所有位置的集合，用于标记哪些位置已经有数据
            positions_with_data = set()
            
            # 首先处理从查询结果中获得的方块数据
            for block_data in blocks:
                # self.logger.info(f"[EnvironmentUpdater] 处理方块数据: {block_data}")
                block_type = block_data.get("name", "")
                can_see = block_data.get("canSee", False)  # 注意：返回的是 canSee，不是 can_see
                x = block_data.get("x", 0)
                y = block_data.get("y", 0)
                z = block_data.get("z", 0)
                
                # 标记这个位置已经有数据
                positions_with_data.add((x, y, z))
                
                # 获取或创建方块位置对象
                block_pos = BlockPosition(x=x, y=y, z=z)
                
                # 更新方块缓存，包括 can_see 信息
                cached_block = global_block_cache.add_block(block_type, can_see, block_pos)
                updated_count += 1
            
            # 然后处理查询范围内但没有数据的位置，设置为air且can_see=True
            for x in range(start_x, end_x + 1):
                for y in range(start_y, end_y + 1):
                    for z in range(start_z, end_z + 1):
                        if (x, y, z) not in positions_with_data:
                            # 这个位置在查询范围内但没有数据，设置为air且can_see=True
                            block_pos = BlockPosition(x=x, y=y, z=z)
                            cached_block = global_block_cache.add_block("air", True, block_pos)
                            updated_count += 1
            
            # self.logger.info(f"[EnvironmentUpdater] 已更新 {updated_count} 个方块的信息")
            return updated_count
            
        except Exception as e:
            self.logger.error(f"[EnvironmentUpdater] 处理 query_area_blocks 数据时出错: {e}")
            self.logger.warning(traceback.format_exc())
            return 0
    
    def stop(self) -> bool:
        """停止环境更新器"""
        if not self.is_running:
            self.logger.warning("[EnvironmentUpdater] 更新器未在运行")
            return False
        
        try:
            self.logger.info("[EnvironmentUpdater] 正在停止更新器...")
            self._stop_event.set()
            
            # 停止异步任务
            if self._update_task and not self._update_task.done():
                self._update_task.cancel()
                self.logger.info("[EnvironmentUpdater] 异步任务已取消")
            
            self.is_running = False
            self.is_paused = False
            self.logger.info("[EnvironmentUpdater] 已停止")
            return True
            
        except Exception as e:
            self.logger.error(f"[EnvironmentUpdater] 停止失败: {e}")
            return False
    
    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop()
    
    def __del__(self):
        """析构函数，确保线程被正确清理"""
        if self.is_running:
            try:
                self.stop()
            except Exception:
                pass

global_environment_updater = EnvironmentUpdater()