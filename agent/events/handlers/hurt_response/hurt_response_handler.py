"""
伤害响应处理器

处理Minecraft中的实体受伤事件，根据伤害来源采取不同的响应策略：
- 玩家攻击：通过LLM进行交涉对话
- 敌对生物攻击：直接反击
- 生命濒危时：请求附近玩家帮助
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
from agent.common.basic_class import Entity
from utils.logger import get_logger

logger = get_logger("HurtResponseHandler")

# 配置参数
HURT_RESPONSE_CONFIG = {
    "enable_damage_interrupt": False,  # 是否启用伤害中断（最高优先级）。由于entityHurt事件存在问题，所以暂时先不启用
    "low_health_threshold": 6,  # 生命濒危阈值（低于此值时请求帮助）
    "critical_health_threshold": 3,  # 生命危急阈值（低于此值时强制中断并寻求治疗）
}


class HurtResponseHandler:
    """伤害响应处理器"""

    def __init__(self):
        self._processing_lock = asyncio.Lock()  # 添加并发锁保护状态更新
        self.setup_listeners()

    def setup_listeners(self):
        """设置事件监听器"""
        # 注册实体受伤事件监听器
        if HURT_RESPONSE_CONFIG["enable_damage_interrupt"]:
            global_event_emitter.on("entityHurt", self.handle_entity_hurt_event)

    async def handle_entity_hurt_event(self, event):
        """处理实体受伤事件 - 根据伤害来源采取相应响应"""
        async with self._processing_lock:  # 使用锁保护状态访问和更新
            try:
                # 检查是否是自己受到了伤害
                if not event.data.entity or not hasattr(event.data.entity, 'username'):
                    return  # 不是玩家实体，忽略

                from config import global_config
                bot_name = global_config.bot.player_name

                # 只处理自己受到的伤害
                if event.data.entity.username != bot_name:
                    return

                # 从事件数据或环境获取生命值
                from agent.environment.environment import global_environment
                current_health = event.data.entity.health if event.data.entity.health is not None else global_environment.health
                damage_source: Optional[Entity] = getattr(event.data, 'source', None)

                logger.info(
                    f"🏥 收到实体受伤事件: 受伤实体 = {event.data.entity.username}, 生命值 = {current_health}, 伤害来源 = {damage_source.username if damage_source else '未知'}"
                )

                # 检查是否生命危急，需要强制中断
                if current_health and current_health <= HURT_RESPONSE_CONFIG["critical_health_threshold"]:
                    logger.critical(f"🚨 生命值危急 ({current_health})！强制中断所有任务并寻求治疗")
                    await self._trigger_critical_health_interrupt(current_health, damage_source)
                    return

                # 触发伤害中断
                await self._trigger_damage_interrupt(current_health, damage_source)

                # 根据伤害来源处理响应
                await self._handle_damage_response(current_health, damage_source)

            except Exception as e:
                logger.error(f"处理实体受伤事件时发生错误: {e}")
                import traceback

                logger.error(f"异常详情: {traceback.format_exc()}")

    async def _trigger_damage_interrupt(self, current_health: Optional[int], damage_source):
        """由于受到伤害触发中断"""
        source_name = damage_source.username if damage_source else "未知来源"

        # 构建中断原因
        reason = f"受到来自 {source_name} 的伤害！当前生命值: {current_health}"

        # 触发移动模块的中断
        global_movement.trigger_interrupt(reason)

        # 记录到思考日志
        global_thinking_log.add_thinking_log(
            f"🚨 受到来自 {source_name} 的伤害！当前生命值: {current_health}，中断当前任务",
            type="damage_interrupt",
        )

        logger.warning(f"伤害中断触发: {reason}")

    async def _trigger_critical_health_interrupt(self, current_health: int, damage_source):
        """生命危急时的强制中断"""
        try:
            source_name = damage_source.username if damage_source else "未知来源"

            # 强制中断所有任务
            reason = f"🚨 生命危急！生命值仅剩 {current_health}，受到来自 {source_name} 的攻击，强制中断所有任务并寻求治疗！"
            global_movement.trigger_interrupt(reason)

            # 记录到思考日志
            global_thinking_log.add_thinking_log(
                f"🚨 生命危急 ({current_health})！受到来自 {source_name} 的致命攻击，强制中断所有任务，优先治疗！",
                type="critical_health_interrupt",
            )

            # 发送紧急求救消息
            await self._send_emergency_distress_call(current_health, damage_source)

            logger.critical(f"生命危急中断触发: {reason}")

        except Exception as e:
            logger.error(f"触发生命危急中断时发生错误: {e}")

    async def _send_emergency_distress_call(self, current_health: int, damage_source):
        """发送紧急求救消息"""
        try:
            mob_name = getattr(damage_source, 'name', None) or "敌对生物"
            mob_type = getattr(damage_source, 'type', None) or "未知生物"

            # 构建紧急求救提示词
            emergency_prompt = f"""我的生命值只剩下 {current_health}/20 了！正在被{ mob_type }({mob_name})攻击，情况非常危急！

请你以我的身份，向附近的玩家发送紧急求救消息，请求立即帮助。

要求：
1. 表达出生命垂危的紧急情况
2. 说明被什么攻击以及剩余生命值
3. 强烈请求玩家立即前来救援
4. 语气要非常焦急和绝望

请只回复求救消息的内容，不要添加其他解释。"""

            # 使用LLM生成紧急求救消息
            from agent.mai_chat import mai_chat
            emergency_message = await mai_chat.llm_client.simple_chat(emergency_prompt)

            # 发送紧急求救消息到聊天
            logger.critical(f"发送紧急求救消息: {emergency_message}")
            await mai_chat.send_message(emergency_message)

            # 记录到思考日志
            global_thinking_log.add_thinking_log(
                f"🚨 紧急求救！生命值仅剩 {current_health}，正在被{ mob_type }攻击: {emergency_message}",
                type="emergency_distress_call",
            )

        except Exception as e:
            logger.error(f"发送紧急求救消息时发生错误: {e}")

    async def _handle_damage_response(
        self, current_health: Optional[int], damage_source: Optional[Entity]
    ):
        """处理伤害响应 - 根据伤害来源选择策略"""
        try:
            logger.info("🔍 开始分析伤害来源并选择响应策略...")

            # 直接从事件数据获取伤害来源信息
            source_type = self._classify_damage_source(damage_source)
            logger.info(f"📊 伤害来源分类结果: {source_type}")

            # 根据伤害来源选择响应策略
            if source_type == "player":
                # 玩家攻击 - 使用聊天工具进行交涉
                logger.info("🎯 玩家攻击，触发交涉逻辑")
                await self._handle_player_attack(damage_source, current_health)
            elif source_type == "hostile_mob":
                # 敌对生物攻击 - 进行反击
                logger.info("⚔️ 敌对生物攻击，触发反击逻辑")
                await self._handle_mob_attack(damage_source, current_health)
            else:
                # 未知伤害来源 - 假设是玩家攻击，尝试交涉
                logger.warning("❓ 无法识别伤害来源，假设为玩家攻击并尝试交涉")
                await self._handle_unknown_damage_as_player(current_health)

        except Exception as e:
            logger.error(f"处理伤害响应时发生错误: {e}")
            import traceback

            logger.error(f"异常详情: {traceback.format_exc()}")

    def _classify_damage_source(self, damage_source: Optional[Entity]) -> str:
        """根据EntityHurtEvent的source字段分类伤害来源"""
        try:
            if not damage_source:
                logger.warning("伤害来源为空，返回未知类型")
                return "unknown"

            # 获取伤害来源的类型信息
            source_type = getattr(damage_source, 'type', None)
            source_name = getattr(damage_source, 'username', None) or getattr(damage_source, 'name', None) or "未知"

            logger.info(f"伤害来源: {source_name}, 类型: {source_type}")

            # 分类逻辑
            if source_type == "player":
                return "player"
            elif source_type == "hostile":
                return "hostile_mob"
            else:
                # 可能是其他玩家或其他未知实体，暂时归类为玩家（会尝试交涉）
                logger.info(f"未知实体类型 {source_type}，假设为玩家")
                return "player"

        except Exception as e:
            logger.error(f"分类伤害来源时发生错误: {e}")
            return "unknown"


    async def _handle_player_attack(
        self, damage_source, current_health: Optional[int]
    ):
        """处理玩家攻击 - 使用聊天进行交涉"""
        player_name = getattr(damage_source, 'username', None) or getattr(damage_source, 'name', None) or "未知玩家"

        # 记录伤害事件
        global_thinking_log.add_thinking_log(
            f"受到玩家 {player_name} 攻击！生命值: {current_health}",
            type="player_attack",
        )

        # 触发专门的玩家交涉提示词
        await self._trigger_player_negotiation_prompt(
            player_name, current_health, damage_source
        )

    async def _handle_mob_attack(
        self, damage_source, current_health: Optional[int]
    ):
        """处理敌对生物攻击 - 进行反击"""
        mob_name = getattr(damage_source, 'name', None) or "敌对生物"
        mob_type = getattr(damage_source, 'type', None) or "未知生物"

        # 记录伤害事件
        global_thinking_log.add_thinking_log(
            f"受到{ mob_type }({mob_name})攻击！生命值: {current_health}",
            type="mob_attack",
        )

        # 检查是否生命濒危，需要求救
        if current_health and current_health <= HURT_RESPONSE_CONFIG["low_health_threshold"]:
            logger.warning(f"生命值过低 ({current_health})，触发求救逻辑")
            await self._trigger_distress_call(current_health, damage_source)
        else:
            # 直接使用kill_mob工具进行反击
            logger.info(f"⚔️ 开始反击 {mob_name}")
            await self._execute_mob_counterattack(damage_source, current_health)

    async def _execute_mob_counterattack(self, damage_source, current_health: int):
        """执行怪物反击逻辑 - 使用kill_mob工具"""
        try:
            mob_name = getattr(damage_source, 'name', None) or "敌对生物"

            # 使用kill_mob工具击杀怪物
            logger.info(f"使用kill_mob工具击杀 {mob_name}")

            # 调用kill_mob工具
            args = {"mob": mob_name}
            call_result = await global_mcp_client.call_tool_directly("kill_mob", args)

            # 解析工具调用结果
            is_success, result_content = parse_tool_result(call_result)

            if is_success:
                logger.info(f"✅ 成功击杀怪物 {mob_name}")
                global_thinking_log.add_thinking_log(
                    f"成功反击并击杀 {mob_name}！",
                    type="mob_counterattack_success",
                )
            else:
                logger.warning(f"击杀怪物 {mob_name} 失败: {result_content}")
                global_thinking_log.add_thinking_log(
                    f"反击 {mob_name} 失败: {result_content}",
                    type="mob_counterattack_failed",
                )
                # 失败时尝试使用AI进行策略性反击
                await self._trigger_mob_combat_prompt(
                    mob_name, getattr(damage_source, 'type', None) or "未知生物",
                    current_health, damage_source
                )

        except Exception as e:
            logger.error(f"执行怪物反击时发生错误: {e}")
            # 发生错误时回退到AI策略
            try:
                mob_name = getattr(damage_source, 'name', None) or "敌对生物"
                mob_type = getattr(damage_source, 'type', None) or "未知生物"
                await self._trigger_mob_combat_prompt(
                    mob_name, mob_type, current_health, damage_source
                )
            except Exception as e2:
                logger.error(f"回退到AI策略也失败: {e2}")

    async def _handle_unknown_damage_as_player(
        self, current_health: Optional[int]
    ):
        """处理未知伤害来源 - 假设是玩家攻击并尝试交涉"""
        logger.warning(f"未知伤害来源，假设为玩家攻击，当前生命值: {current_health}")

        # 创建一个模拟的玩家伤害源对象
        class MockPlayerSource:
            def __init__(self):
                self.type = "player"
                self.username = "附近玩家"
                self.name = "附近玩家"

        mock_player_source = MockPlayerSource()

        # 触发玩家交涉逻辑
        await self._handle_player_attack(
            mock_player_source, current_health
        )

    async def _trigger_player_negotiation_prompt(
        self, player_name: str, current_health: int, damage_source
    ):
        """触发玩家交涉提示词"""
        try:
            # 构建专门的玩家交涉提示词
            negotiation_prompt = await self._build_player_negotiation_prompt(
                player_name, current_health, damage_source
            )

            # 调用AI系统处理专门的玩家交涉提示词
            logger.info(f"触发玩家交涉提示词: {player_name}")
            await self._process_ai_negotiation(
                negotiation_prompt, player_name, current_health
            )

        except Exception as e:
            logger.error(f"触发玩家交涉提示词时发生错误: {e}")

    async def _trigger_distress_call(self, current_health: int, damage_source):
        """触发求救逻辑 - 当生命濒危时请求附近玩家帮助"""
        try:
            mob_name = getattr(damage_source, 'name', None) or "敌对生物"
            mob_type = getattr(damage_source, 'type', None) or "未知生物"

            # 构建求救提示词
            distress_prompt = f"""我正在被{ mob_type }({mob_name})攻击！生命值只剩下 {current_health}/20 了，非常危险！

请你以我的身份，向附近的玩家发送求救消息，请求他们来救我。

要求：
1. 表达出生命濒危的紧急情况
2. 说明被什么攻击（{ mob_type }）
3. 请求玩家尽快来帮忙
4. 语气要恳求和焦急

请只回复求救消息的内容，不要添加其他解释。"""

            # 使用LLM生成求救消息
            from agent.mai_chat import mai_chat
            distress_message = await mai_chat.llm_client.simple_chat(distress_prompt)

            # 发送求救消息到聊天
            logger.warning(f"发送求救消息: {distress_message}")
            await mai_chat.send_message(distress_message)

            # 记录到思考日志
            global_thinking_log.add_thinking_log(
                f"🚨 生命濒危 ({current_health})！向玩家求救: {distress_message}",
                type="distress_call",
            )

        except Exception as e:
            logger.error(f"触发求救逻辑时发生错误: {e}")

    async def _process_ai_negotiation(
        self, negotiation_prompt: str, player_name: str, current_health: int
    ):
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
            default_message = (
                f"嘿 {player_name}，为什么攻击我？我不想战斗，能不能谈谈？"
            )
            await self._send_chat_message(default_message)

    async def _send_chat_message(self, message: str):
        """发送聊天消息"""
        try:
            from fastmcp.client.client import CallToolResult
            from agent.utils.utils import parse_tool_result

            args = {"message": message}
            call_result: CallToolResult = await global_mcp_client.call_tool_directly(
                "chat", args
            )
            is_success, result_content = parse_tool_result(call_result)

            if is_success:
                global_thinking_log.add_thinking_log(
                    f"发送交涉消息: {message}", type="notice"
                )
                logger.info(f"成功发送交涉消息: {message}")
            else:
                logger.error(f"发送交涉消息失败: {result_content}")

        except Exception as e:
            logger.error(f"发送聊天消息时发生错误: {e}")

    async def _trigger_mob_combat_prompt(
        self, mob_name: str, mob_type: str, current_health: int, damage_source
    ):
        """触发敌对生物反击提示词"""
        try:
            # 构建专门的反击提示词
            combat_prompt = self._build_mob_combat_prompt(
                mob_name, mob_type, current_health, damage_source
            )

            # 调用AI系统处理专门的反击提示词
            logger.info(f"触发敌对生物反击提示词: {mob_name}")
            await self._process_ai_combat(
                combat_prompt, mob_name, current_health, damage_source
            )

        except Exception as e:
            logger.error(f"触发敌对生物反击提示词时发生错误: {e}")

    async def _process_ai_combat(
        self,
        combat_prompt: str,
        mob_name: str,
        current_health: int,
        damage_source: dict,
    ):
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
            await self._execute_combat_actions(
                thinking_reply, mob_name, current_health, damage_source
            )

        except Exception as e:
            logger.error(f"处理AI反击逻辑时发生错误: {e}")
            # 发生错误时执行默认反击策略
            await self._execute_default_combat_strategy(
                mob_name, current_health, damage_source
            )

    async def _execute_combat_actions(
        self, ai_reply: str, mob_name: str, current_health: int, damage_source: dict
    ):
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

    async def _execute_default_combat_strategy(
        self, mob_name: str, current_health: int, damage_source: dict
    ):
        """执行默认战斗策略"""
        try:
            logger.info(f"执行默认反击策略对 {mob_name}")
            await self._prepare_combat_response(mob_name, current_health)
        except Exception as e:
            logger.error(f"执行默认战斗策略时发生错误: {e}")

    async def _build_player_negotiation_prompt(
        self, player_name: str, current_health: int, damage_source
    ) -> str:
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
                    nearby_block_info = (
                        await nearby_block_manager.get_visible_blocks_str(
                            global_environment.block_position, distance=16
                        )
                    )
                except Exception as e:
                    logger.debug(f"获取周围方块信息失败: {e}")

            # 获取周围箱子信息
            from agent.container_cache.container_cache import global_container_cache

            container_cache_info = ""
            if global_environment.block_position:
                container_cache_info = (
                    global_container_cache.get_nearby_containers_info(
                        global_environment.block_position, 3
                    )
                )

            # 获取周围实体信息
            nearby_entities_info = global_environment.get_nearby_entities_info()

            # 获取聊天记录
            chat_str = global_chat_history.get_chat_history_str()
            # 添加本次攻击事件
            attack_msg = f"[刚刚] {player_name} 攻击了你"
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

        # 使用提示词模板生成提示词
        return prompt_manager.generate_prompt(
            "health_player_negotiation",
            bot_name=bot_name,
            player_name_game=player_name_game,
            current_health=current_health,
            goal=goal,
            to_do_list=to_do_list,
            self_status_info=self_status_info,
            inventory_info=inventory_info,
            position=position,
            nearby_block_info=nearby_block_info,
            container_cache_info=container_cache_info,
            nearby_entities_info=nearby_entities_info,
            chat_str=chat_str
        )

    def _build_mob_combat_prompt(
        self, mob_name: str, mob_type: str, current_health: int, damage_source
    ) -> str:
        """构建敌对生物反击提示词"""
        from agent.prompt_manager.prompt_manager import prompt_manager

        return prompt_manager.generate_prompt(
            "health_mob_combat",
            mob_name=mob_name,
            mob_type=mob_type,
            current_health=current_health
        )


    async def _prepare_combat_response(self, mob_name: str, current_health: int):
        """准备战斗响应"""
        try:
            logger.info(f"准备对抗 {mob_name}，当前生命值: {current_health}")

            # 检查生命值，如果过低则考虑逃跑而不是战斗
            if current_health < 10:
                logger.warning(f"生命值过低 ({current_health})，考虑逃跑而不是战斗")
                global_thinking_log.add_thinking_log(
                    f"⚠️ 生命值过低 ({current_health})，准备逃跑而不是与 {mob_name} 战斗",
                    type="combat_preparation",
                )
                return

            # 记录战斗意图到思考日志
            global_thinking_log.add_thinking_log(
                f"⚔️ 准备反击 {mob_name}，当前生命值: {current_health}",
                type="combat_preparation",
            )

            # 这里可以添加更多的战斗准备逻辑：
            # 1. 检查并装备最佳武器
            # 2. 确保有足够的弹药/耐久
            # 3. 移动到有利战斗位置
            # 4. 评估周围环境

            logger.info(f"战斗准备完成，随时准备反击 {mob_name}")

        except Exception as e:
            logger.error(f"准备战斗响应时发生错误: {e}")


# 便捷函数
def get_health_status():
    """获取当前健康状态"""
    from agent.environment.environment import global_environment
    health_status = global_environment.get_health_status()
    return {
        "last_health": health_status["last_health"],
        "current_health": health_status["current_health"],
        "has_damage": health_status["has_damage"],
        "config": HURT_RESPONSE_CONFIG.copy()
    }


def update_hurt_response_config(new_config: dict):
    """更新伤害响应配置"""
    global HURT_RESPONSE_CONFIG
    HURT_RESPONSE_CONFIG.update(new_config)
    logger.info(f"更新伤害响应配置: {new_config}")


# 创建全局伤害响应处理器实例
global_hurt_response_handler = HurtResponseHandler()


def setup_hurt_response_handlers():
    """
    设置伤害响应处理器

    这个函数会在系统初始化时被调用，注册所有伤害响应相关的事件处理器。
    处理器在模块导入时就会被创建，这里主要是为了保持API一致性。
    """
    logger.info("设置伤害响应处理器...")
    # 处理器已经在模块导入时创建并注册，这里可以添加额外的设置逻辑
    pass
