"""
健康事件处理器

处理Minecraft中的健康相关事件，特别是当生命值过低时中断当前任务进行紧急处理。
"""

import asyncio
from typing import Optional
from agent.events import global_event_emitter
from agent.environment.movement import global_movement
from agent.thinking_log import global_thinking_log
from agent.events import global_event_store, EventType
from agent.prompt_manager.prompt_manager import prompt_manager
from mcp_server.client import global_mcp_client
from agent.utils.utils import parse_tool_result
from utils.logger import get_logger

logger = get_logger("HealthEventHandler")

# 配置参数
HEALTH_CONFIG = {
    "enable_damage_interrupt": True,  # 是否启用伤害中断（最高优先级）
}

class HealthEventHandler:
    """健康事件处理器"""

    def __init__(self):
        self.last_health = None
        self._processing_lock = asyncio.Lock()  # 添加并发锁保护状态更新
        self.setup_listeners()

    def setup_listeners(self):
        """设置事件监听器"""
        # 注册健康事件监听器
        global_event_emitter.on('health', self.handle_health_event)

    async def handle_health_event(self, event):
                """处理健康事件 - 只要受到伤害就立即中断"""
                async with self._processing_lock:  # 使用锁保护状态访问和更新
                    try:
                        current_health = event.data.health
                        logger.info(f"🏥 收到健康事件: 生命值 = {current_health}, 上一生命值 = {self.last_health}")

                        # 核心逻辑：只要生命值下降就立即中断！
                        if self._has_taken_damage(current_health):
                            damage_taken = self.last_health - current_health if self.last_health else 0
                            logger.warning(f"⚠️ 检测到伤害: 损失 {damage_taken} 点生命值，从 {self.last_health} 降至 {current_health}")
                            await self._trigger_damage_interrupt(current_health)

                            # 🚨 新增：触发专门的伤害响应处理
                            await self._handle_damage_response(current_health, damage_taken)
                        else:
                            logger.debug(f"生命值未下降，无需响应 (当前: {current_health}, 上次: {self.last_health})")

                        # 更新状态
                        old_health = self.last_health
                        self.last_health = current_health
                        if old_health != current_health:
                            logger.debug(f"更新last_health: {old_health} -> {current_health}")

                    except Exception as e:
                        logger.error(f"处理健康事件时发生错误: {e}")
                        import traceback
                        logger.error(f"异常详情: {traceback.format_exc()}")

    def _has_taken_damage(self, current_health: Optional[int]) -> bool:
        """判断是否受到伤害（生命值下降）"""
        if current_health is None or self.last_health is None:
            return False

        # 如果当前生命值低于上一次记录的生命值，说明受到了伤害
        return current_health < self.last_health

    async def _trigger_damage_interrupt(self, current_health: Optional[int]):
        """由于受到伤害触发中断"""
        damage_taken = self.last_health - current_health if self.last_health and current_health else "未知"

        # 构建中断原因
        reason = f"受到伤害！生命值下降 {damage_taken} 点，当前生命值: {current_health}"

        # 触发移动模块的中断
        global_movement.trigger_interrupt(reason)

        # 记录到思考日志
        global_thinking_log.add_thinking_log(
            f"🚨 受到伤害！生命值从 {self.last_health} 降至 {current_health}，中断当前任务",
            type="damage_interrupt"
        )

        logger.warning(f"伤害中断触发: {reason}")

        # 注意：伤害响应处理已在handle_health_event中调用，这里不再重复调用

    async def _handle_damage_response(self, current_health: Optional[int], damage_taken):
                """处理伤害响应 - 使用专门的提示词"""
                try:
                    logger.info("🔍 开始识别伤害来源...")
                    # 识别伤害来源
                    damage_source = await self._identify_damage_source()
                    logger.info(f"📊 伤害来源识别结果: {damage_source}")

                    # 根据伤害来源选择响应策略
                    if damage_source.get("type") == "player":
                        # 玩家攻击 - 使用聊天工具进行交涉
                        logger.info("🎯 识别为玩家攻击，触发交涉逻辑")
                        await self._handle_player_attack(damage_source, current_health, damage_taken)
                    elif damage_source.get("type") == "hostile_mob":
                        # 敌对生物攻击 - 进行反击
                        logger.info("⚔️ 识别为敌对生物攻击，触发反击逻辑")
                        await self._handle_mob_attack(damage_source, current_health, damage_taken)
                    else:
                        # 未知伤害来源 - 假设是玩家攻击，尝试交涉
                        logger.warning("❓ 无法识别伤害来源，假设为玩家攻击并尝试交涉")
                        await self._handle_unknown_damage_as_player(current_health, damage_taken)

                except Exception as e:
                    logger.error(f"处理伤害响应时发生错误: {e}")
                    import traceback
                    logger.error(f"异常详情: {traceback.format_exc()}")

    async def _identify_damage_source(self) -> dict:
        """识别伤害来源"""
        try:
            # 获取bot自己的名字，避免把自己识别为伤害来源
            from config import global_config
            bot_name = global_config.bot.player_name
            logger.info(f"Bot名字: {bot_name}")

            # 方法1：检查最近的entityHurt事件
            recent_hurt_events = await self._get_recent_hurt_events()
            logger.info(f"找到 {len(recent_hurt_events)} 个最近的entityHurt事件")

            if recent_hurt_events:
                # 优先分析最新的伤害事件（最近的那个）
                latest_event = recent_hurt_events[-1]  # 列表中最后一个是最新的
                logger.info("所有entityHurt事件:")
                for i, event in enumerate(recent_hurt_events):
                    logger.info(f"  [{i}] {event.type} - {event.data}")
                logger.info(f"选择最新的entityHurt事件 [-1]: {latest_event.type}, 数据: {latest_event.data}")

                if hasattr(latest_event, 'data') and latest_event.data and latest_event.data.get('entity'):
                    entity = latest_event.data['entity']
                    logger.info(f"最新实体信息: {entity}")

                    # 处理Entity对象或字典
                    if hasattr(entity, 'type'):  # Entity对象
                        entity_type = entity.type
                        entity_name = getattr(entity, 'username', None) or getattr(entity, 'name', None) or "未知"
                    else:  # 字典
                        entity_type = entity.get('type')
                        entity_name = entity.get('username', entity.get('name', '未知'))

                    logger.info(f"实体类型: {entity_type}, 名称: {entity_name}")

                    # entityHurt事件中的entity是受伤者，不是攻击者
                    if entity_name == bot_name:
                        logger.info(f"✅ entityHurt事件确认bot({bot_name})受到了伤害，现在寻找最近的非bot实体作为攻击者")
                        # 确认bot受到伤害，继续寻找攻击者
                    elif entity_name != bot_name:
                        # 如果entityHurt事件中的实体不是bot自己，那可能是其他实体受到了伤害
                        # 这可能不是我们关心的伤害事件
                        logger.debug(f"entityHurt事件中的受伤者不是bot自己: {entity_name}")
                        # 继续检查，可能有其他相关的伤害事件

            # 方法2：检查周围的实体（寻找最近的非bot实体作为可能的攻击者）
            nearby_entities = await self._get_nearby_entities()
            logger.info(f"找到 {len(nearby_entities)} 个周围实体")

            # 筛选出非bot的实体，并按距离排序（最近的优先）
            potential_attackers = []
            for entity in nearby_entities:
                # 处理Entity对象或字典
                if hasattr(entity, 'type'):  # Entity对象
                    entity_type = entity.type
                    entity_name = getattr(entity, 'username', None) or getattr(entity, 'name', None) or "未知"
                    entity_distance = getattr(entity, 'distance', 100)  # 默认距离100
                else:  # 字典
                    entity_type = entity.get('type')
                    entity_name = entity.get('username', entity.get('name', '未知'))
                    entity_distance = entity.get('distance', 100)

                logger.info(f"检查周围实体: {entity_type} - {entity_name} (距离: {entity_distance})")

                # 跳过bot自己
                if entity_name == bot_name:
                    logger.debug(f"跳过bot自己: {entity_name}")
                    continue

                # 收集可能的攻击者（玩家和敌对生物）
                if entity_type == 'player' or entity_type in ['zombie', 'skeleton', 'spider', 'creeper', 'enderman']:
                    potential_attackers.append({
                        'entity': entity,
                        'type': entity_type,
                        'name': entity_name,
                        'distance': entity_distance,
                        'is_player': entity_type == 'player'
                    })

            # 按距离排序（最近的优先），玩家优先于怪物
            potential_attackers.sort(key=lambda x: (0 if x['is_player'] else 1, x['distance']))

            # 返回最近的可能的攻击者
            if potential_attackers:
                closest_attacker = potential_attackers[0]
                attacker_type = "player" if closest_attacker['is_player'] else "hostile_mob"
                logger.info(f"🎯 选择最近的可能攻击者: {closest_attacker['name']} (类型: {attacker_type}, 距离: {closest_attacker['distance']})")

                return {
                    "type": attacker_type,
                    "name": closest_attacker['name'],
                    "entity": closest_attacker['entity']
                }

            logger.warning("未找到明确的伤害来源（没有entityHurt事件或周围没有可疑实体）")
            return {"type": "unknown", "name": "未知"}

        except Exception as e:
            logger.error(f"识别伤害来源时发生错误: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"type": "unknown", "name": "未知"}

    async def _get_recent_hurt_events(self):
        """获取最近的entityHurt事件"""
        try:
            # 从事件存储中获取最近的entityHurt事件
            return global_event_store.get_events_by_type(EventType.ENTITY_HURT.value, limit=10)
        except Exception as e:
            logger.error(f"获取最近伤害事件时发生错误: {e}")
            return []

    async def _get_nearby_entities(self):
        """获取周围实体"""
        try:
            # 延迟导入以避免循环引用
            from agent.environment.environment import global_environment
            return global_environment.nearby_entities
        except Exception as e:
            logger.error(f"获取周围实体时发生错误: {e}")
            return []

    async def _handle_player_attack(self, damage_source: dict, current_health: Optional[int], damage_taken):
        """处理玩家攻击 - 使用聊天进行交涉"""
        player_name = damage_source.get("name", "未知玩家")

        # 记录伤害事件
        global_thinking_log.add_thinking_log(
            f"⚔️ 受到玩家 {player_name} 攻击！生命值: {current_health}",
            type="player_attack"
        )

        # 触发专门的玩家交涉提示词
        await self._trigger_player_negotiation_prompt(player_name, current_health, damage_taken, damage_source)

    async def _handle_mob_attack(self, damage_source: dict, current_health: Optional[int], damage_taken):
        """处理敌对生物攻击 - 进行反击"""
        mob_name = damage_source.get("name", "敌对生物")

        # 记录伤害事件
        global_thinking_log.add_thinking_log(
            f"👹 受到敌对生物 {mob_name} 攻击！生命值: {current_health}",
            type="mob_attack"
        )

        # 触发专门的反击提示词
        await self._trigger_mob_combat_prompt(mob_name, current_health, damage_taken, damage_source)

    async def _handle_unknown_damage_as_player(self, current_health: Optional[int], damage_taken):
        """处理未知伤害来源 - 假设是玩家攻击并尝试交涉"""
        logger.warning(f"未知伤害来源，假设为玩家攻击，当前生命值: {current_health}")

        # 创建一个模拟的玩家伤害源
        mock_player_source = {
            "type": "player",
            "name": "附近玩家",  # 通用名称，因为无法识别具体玩家
            "entity": None
        }

        # 触发玩家交涉逻辑
        await self._handle_player_attack(mock_player_source, current_health, damage_taken)

    async def _handle_unknown_damage(self, damage_source: dict, current_health: Optional[int], damage_taken):
        """处理未知伤害来源"""
        global_thinking_log.add_thinking_log(
            f"❓ 受到未知伤害来源攻击！生命值: {current_health}",
            type="unknown_damage"
        )

        logger.info("触发未知伤害处理")

    async def _trigger_player_negotiation_prompt(self, player_name: str, current_health: int, damage_taken, damage_source: dict):
        """触发玩家交涉提示词"""
        try:
            # 构建专门的玩家交涉提示词
            negotiation_prompt = await self._build_player_negotiation_prompt(player_name, current_health, damage_taken, damage_source)

            # 调用AI系统处理专门的玩家交涉提示词
            logger.info(f"触发玩家交涉提示词: {player_name}")
            await self._process_ai_negotiation(negotiation_prompt, player_name, current_health)

        except Exception as e:
            logger.error(f"触发玩家交涉提示词时发生错误: {e}")

    async def _process_ai_negotiation(self, negotiation_prompt: str, player_name: str, current_health: int):
        """处理AI交涉逻辑"""
        try:
            # 延迟导入mai_chat以避免循环导入
            from agent.mai_chat import mai_chat
            # 使用mai_chat的LLM客户端处理交涉提示词
            thinking_reply = await mai_chat.llm_client.simple_chat(negotiation_prompt)

            # AI直接返回聊天内容，直接使用
            message = thinking_reply.strip() if thinking_reply else ""

            if message and len(message) > 2:
                logger.info(f"AI生成交涉消息: {message}")
                await self._send_chat_message(message)
                return

            # 如果回复为空或太短，使用默认消息
            logger.warning("AI回复为空或太短，使用默认消息")
            default_message = f"诶 {player_name}，你干嘛打我啊？有啥误会吗？"
            await self._send_chat_message(default_message)

        except Exception as e:
            logger.error(f"处理AI交涉逻辑时发生错误: {e}")
            # 发生错误时发送默认消息
            default_message = f"嘿 {player_name}，为什么攻击我？我不想战斗，能不能谈谈？"
            await self._send_chat_message(default_message)

    async def _send_chat_message(self, message: str):
        """发送聊天消息"""
        try:
            from fastmcp.client.client import CallToolResult
            from agent.utils.utils import parse_tool_result

            args = {"message": message}
            call_result: CallToolResult = await global_mcp_client.call_tool_directly("chat", args)
            is_success, result_content = parse_tool_result(call_result)

            if is_success:
                global_thinking_log.add_thinking_log(f"发送交涉消息: {message}", type="notice")
                logger.info(f"成功发送交涉消息: {message}")
            else:
                logger.error(f"发送交涉消息失败: {result_content}")

        except Exception as e:
            logger.error(f"发送聊天消息时发生错误: {e}")

    async def _trigger_mob_combat_prompt(self, mob_name: str, current_health: int, damage_taken, damage_source: dict):
        """触发敌对生物反击提示词"""
        try:
            # 构建专门的反击提示词
            combat_prompt = self._build_mob_combat_prompt(mob_name, current_health, damage_taken, damage_source)

            # 调用AI系统处理专门的反击提示词
            logger.info(f"触发敌对生物反击提示词: {mob_name}")
            await self._process_ai_combat(combat_prompt, mob_name, current_health, damage_source)

        except Exception as e:
            logger.error(f"触发敌对生物反击提示词时发生错误: {e}")

    async def _process_ai_combat(self, combat_prompt: str, mob_name: str, current_health: int, damage_source: dict):
        """处理AI反击逻辑"""
        try:
            # 延迟导入mai_chat以避免循环导入
            from agent.mai_chat import mai_chat
            # 使用mai_chat的LLM客户端处理反击提示词
            thinking_reply = await mai_chat.llm_client.simple_chat(combat_prompt)

            # 解析AI回复，提取战斗动作
            # AI回复应该包含战斗策略，如装备武器、移动位置等
            logger.info(f"AI反击回复: {thinking_reply}")

            # 解析并执行战斗动作
            await self._execute_combat_actions(thinking_reply, mob_name, current_health, damage_source)

        except Exception as e:
            logger.error(f"处理AI反击逻辑时发生错误: {e}")
            # 发生错误时执行默认反击策略
            await self._execute_default_combat_strategy(mob_name, current_health, damage_source)

    async def _execute_combat_actions(self, ai_reply: str, mob_name: str, current_health: int, damage_source: dict):
        """执行战斗动作"""
        try:
            # 解析AI回复，提取战斗指令
            # 这里应该解析AI的回复并执行相应的战斗动作
            # 例如：装备武器、移动到有利位置、攻击等

            # 临时实现：记录战斗意图并执行基本战斗准备
            logger.info(f"开始执行对 {mob_name} 的反击策略")
            await self._prepare_combat_response(mob_name, current_health)

        except Exception as e:
            logger.error(f"执行战斗动作时发生错误: {e}")

    async def _execute_default_combat_strategy(self, mob_name: str, current_health: int, damage_source: dict):
        """执行默认战斗策略"""
        try:
            logger.info(f"执行默认反击策略对 {mob_name}")
            await self._prepare_combat_response(mob_name, current_health)
        except Exception as e:
            logger.error(f"执行默认战斗策略时发生错误: {e}")

    async def _build_player_negotiation_prompt(self, player_name: str, current_health: int, damage_taken, damage_source: dict) -> str:
        """构建玩家交涉提示词"""
        # 获取环境信息
        try:
            from agent.prompt_manager.prompt_manager import prompt_manager
            from agent.environment.environment import global_environment
            from agent.to_do_list import mai_to_do_list, mai_goal
            from config import global_config
            from agent.chat_history import global_chat_history
            from agent.block_cache.nearby_block import nearby_block_manager

            # 获取基本信息
            bot_name = "EvilMai"
            player_name_game = global_config.bot.player_name

            # 获取任务信息
            goal = mai_goal.goal
            to_do_list = str(mai_to_do_list)

            # 获取当前状态
            self_status_info = f"生命值: {current_health}/20"

            # 获取物品栏信息
            inventory_info = global_environment.get_inventory_info()

            # 获取位置信息
            position = global_environment.get_position_str()

            # 获取周围方块信息
            nearby_block_info = "周围方块信息不可用"
            if global_environment.block_position:
                try:
                    nearby_block_info = await nearby_block_manager.get_visible_blocks_str(
                        global_environment.block_position, distance=16)
                except Exception as e:
                    logger.debug(f"获取周围方块信息失败: {e}")

            # 获取周围箱子信息
            from agent.container_cache.container_cache import global_container_cache
            container_cache_info = ""
            if global_environment.block_position:
                container_cache_info = global_container_cache.get_nearby_containers_info(global_environment.block_position, 3)

            # 获取周围实体信息
            nearby_entities_info = global_environment.get_nearby_entities_info()

            # 获取聊天记录
            chat_str = global_chat_history.get_chat_history_str()
            # 添加本次攻击事件
            attack_msg = f"[刚刚] {player_name} 攻击了你，造成 {damage_taken} 点伤害"
            chat_str = f"{attack_msg}\n{chat_str}" if chat_str else attack_msg

        except Exception as e:
            logger.warning(f"获取环境信息失败，使用默认值: {e}")
            import traceback
            logger.debug(f"环境信息获取异常详情: {traceback.format_exc()}")

            # 使用默认值
            bot_name = "EvilMai"
            player_name_game = "EvilMai"
            goal = "挖到16个钻石并存储"
            to_do_list = "正在挖矿收集钻石..."
            self_status_info = f"生命值: {current_health}/20"
            inventory_info = "石镐、石剑等工具"
            position = "地下矿洞中"
            nearby_block_info = "周围是石头和矿石"
            container_cache_info = "附近有箱子"
            nearby_entities_info = f"附近有玩家 {player_name}"
            chat_str = f"[刚刚] {player_name} 攻击了你"

        return f"""
你是{bot_name}，游戏名叫{player_name_game},你正在游玩Minecraft，是一名Minecraft玩家。
刚刚有人攻击了你，损失了 {damage_taken} 点生命值，当前生命值是 {current_health}。

**当前目标和任务列表**：
目标：{goal}
任务列表：
{to_do_list}

**当前状态**
{self_status_info}

**物品栏和工具**
{inventory_info}

**位置信息**
{position}

**周围方块的信息**
{nearby_block_info}

**周围箱子信息**
{container_cache_info}

**周围实体信息**
{nearby_entities_info}

**玩家聊天记录**：
{chat_str}

刚刚有人攻击了你，造成 {damage_taken} 点伤害。你需要回复这个攻击行为。

**回复要求**
- 简短直接，可以参考微博、贴吧的语气
- 表现出惊讶或困惑，但保持友好
- 想了解对方为什么攻击你，不想继续战斗
- 直接回复聊天内容，不要添加多余格式
"""

    def _build_mob_combat_prompt(self, mob_name: str, current_health: int, damage_taken, damage_source: dict) -> str:
        """构建敌对生物反击提示词"""
        return f"""
你刚刚受到敌对生物 {mob_name} 的攻击，损失了 {damage_taken} 点生命值，当前生命值是 {current_health}。

请立即进行反击：
1. 装备合适的武器
2. 锁定目标并攻击
3. 保持安全距离
4. 如果生命值过低，考虑逃跑或寻找掩体

优先保护自己生命安全，同时消灭威胁。
"""

    async def _send_negotiation_chat(self, player_name: str, current_health: int):
        """发送交涉聊天消息（已废弃，由AI处理替代）"""
        # 这个方法现在已被 _process_ai_negotiation 替代
        # 保留以防向后兼容性需求
        pass

    async def _prepare_combat_response(self, mob_name: str, current_health: int):
        """准备战斗响应"""
        try:
            logger.info(f"准备对抗 {mob_name}，当前生命值: {current_health}")

            # 检查生命值，如果过低则考虑逃跑而不是战斗
            if current_health < 10:
                logger.warning(f"生命值过低 ({current_health})，考虑逃跑而不是战斗")
                global_thinking_log.add_thinking_log(
                    f"⚠️ 生命值过低 ({current_health})，准备逃跑而不是与 {mob_name} 战斗",
                    type="combat_preparation"
                )
                return

            # 记录战斗意图到思考日志
            global_thinking_log.add_thinking_log(
                f"⚔️ 准备反击 {mob_name}，当前生命值: {current_health}",
                type="combat_preparation"
            )

            # 这里可以添加更多的战斗准备逻辑：
            # 1. 检查并装备最佳武器
            # 2. 确保有足够的弹药/耐久
            # 3. 移动到有利战斗位置
            # 4. 评估周围环境

            logger.info(f"战斗准备完成，随时准备反击 {mob_name}")

        except Exception as e:
            logger.error(f"准备战斗响应时发生错误: {e}")

# 全局健康事件处理器实例
health_handler = HealthEventHandler()

# 便捷函数
def get_health_status():
    """获取当前健康状态"""
    return {
        "last_health": health_handler.last_health,
        "config": HEALTH_CONFIG.copy()
    }

def update_health_config(new_config: dict):
    """更新健康配置"""
    global HEALTH_CONFIG
    HEALTH_CONFIG.update(new_config)
    logger.info(f"更新健康配置: {new_config}")

def setup_health_handlers():
    """
    设置健康事件处理器

    这个函数会在系统初始化时被调用，注册所有健康相关的事件处理器。
    处理器在模块导入时就会被创建，这里主要是为了保持API一致性。
    """
    logger.info("设置健康事件处理器...")
    # 处理器已经在模块导入时创建并注册，这里可以添加额外的设置逻辑
    pass
