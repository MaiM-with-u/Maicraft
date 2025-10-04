"""
战斗模式处理器

集中管理所有战斗模式的逻辑：
- 威胁检测和评估
- 模式切换管理
- 自动攻击执行
- 状态监控和超时处理

实现 ModeHandler 接口，与模式系统解耦
"""

import asyncio
import time
from typing import List, Tuple, Optional, Dict, Any
from agent.modes.base import ModeHandler
from agent.mai_mode import MaiModeType, ModeTransition, EnvironmentListener
from agent.environment.movement import global_movement
from agent.thinking_log import global_thinking_log
from mcp_server.client import global_mcp_client
from agent.utils.utils import parse_tool_result
from agent.common.basic_class import Entity
from utils.logger import get_logger

logger = get_logger("CombatHandler")


class CombatHandler(ModeHandler, EnvironmentListener):
    """战斗模式处理器"""

    def __init__(self):
        self._processing_lock = asyncio.Lock()

        # 敌对生物名称列表
        self.hostile_entity_names = {
            'zombie', 'skeleton', 'creeper', 'spider', 'enderman', 'witch',
            'blaze', 'ghast', 'magma_cube', 'slime', 'guardian', 'elder_guardian',
            'wither_skeleton', 'stray', 'husk', 'drowned', 'phantom', 'zombie_villager',
            'skeleton_horse', 'zombie_horse', 'evoker', 'vindicator', 'pillager',
            'ravager', 'vex', 'warden'
        }

        # 战斗状态管理
        self.active_threats: List[Tuple[Entity, float]] = []  # (entity, distance)
        self.threat_count = 0
        self.in_combat_mode = False

        # 从全局配置加载威胁检测配置
        try:
            from config import global_config
            threat_config = global_config.threat_detection

            self.detection_config = {
                "threat_detection_distance": threat_config.threat_detection_range,  # 威胁检测距离
                "threat_min_distance": threat_config.threat_detection_range * 0.5,  # 最小威胁距离（超过此距离停止警戒）
                "threat_timeout": 300,  # 威胁状态超时时间（秒）
                "attack_interval": 2.0,  # 攻击间隔（秒）
                "max_attack_attempts": 5,  # 最大攻击尝试次数
                "enabled": threat_config.enable_threat_detection,  # 是否启用威胁检测
            }
        except Exception as e:
            logger.warning(f"加载威胁检测配置失败，使用默认配置: {e}")
            self.detection_config = {
                "threat_detection_distance": 16.0,  # 威胁检测距离
                "threat_min_distance": 8.0,  # 最小威胁距离（超过此距离停止警戒）
                "threat_timeout": 180,  # 威胁状态超时时间（3分钟）
                "attack_interval": 1.5,  # 攻击间隔（秒）
                "max_attack_attempts": 3,  # 最大攻击尝试次数
                "enabled": True,  # 是否启用威胁检测
            }

        # 状态跟踪
        self.last_attack_time = 0
        self.threat_start_time: Optional[float] = None
        self.attack_attempts: Dict[str, int] = {}  # 记录对每个敌人的攻击次数

        # 自动恢复任务
        self._recovery_task: Optional[asyncio.Task] = None

        # 注册状态跟踪
        self._registration_failed = False


        logger.debug("战斗模式处理器初始化完成")

    def _register_as_environment_listener(self):
        """注册为环境监听器"""
        try:
            from agent.mai_mode import mai_mode
            mai_mode.register_handler(self)  # 注册为模式处理器
            mai_mode.register_environment_listener(self)  # 注册为环境监听器
            logger.debug("战斗处理器已注册为模式处理器和环境监听器")

        except Exception as e:
            logger.error(f"注册失败: {e}")
            # 注册失败，设置一个标志，在下次访问时重试
            self._registration_failed = True

    def _ensure_registered(self):
        """确保已注册到模式系统"""
        try:
            from agent.mai_mode import mai_mode

            # 检查是否需要注册（未注册或之前注册失败）
            handler_registered = mai_mode.get_handler(self.mode_type) == self
            listener_registered = self in mai_mode._environment_listeners

            if not handler_registered or not listener_registered or self._registration_failed:
                logger.info(f"重新注册战斗处理器 - 处理器: {handler_registered}, 监听器: {listener_registered}, 之前失败: {self._registration_failed}")

                if not handler_registered:
                    mai_mode.register_handler(self)  # 注册为模式处理器

                if not listener_registered:
                    mai_mode.register_environment_listener(self)  # 注册为环境监听器

                logger.debug("战斗处理器重新注册完成")

                # 重置失败标志
                self._registration_failed = False

        except Exception as e:
            logger.error(f"重新注册失败: {e}")
            self._registration_failed = True

    async def on_environment_updated(self, environment_data: Dict[str, Any]) -> None:
        """实现 EnvironmentListener 接口：处理环境更新"""
        try:
            # 每次环境更新都确保已注册（处理初始化顺序问题）
            self._ensure_registered()

            # 只处理实体更新
            update_type = environment_data.get("update_type")
            if update_type != "entity_update":
                return

            nearby_entities = environment_data.get("nearby_entities", [])
            # 检查是否有敌对生物
            hostile_entities = []
            for e in nearby_entities:
                if isinstance(e, dict):
                    # 检查多种可能的敌对标识
                    entity_type = e.get("type", "")
                    entity_name = e.get("name", "").lower()

                    is_hostile = (
                        entity_type == "hostile" or
                        entity_name in self.hostile_entity_names or
                        any(keyword in entity_name for keyword in ["zombie", "skeleton", "creeper", "spider"])
                    )

                    if is_hostile:
                        hostile_entities.append(e)

            # 直接基于原始数据检测威胁并切换模式
            await self._process_threat_detection(nearby_entities)

        except Exception as e:
            logger.error(f"处理环境更新时出错: {e}")

    async def _process_threat_detection(self, nearby_entities: List[dict]) -> None:
        """
        直接基于原始数据处理威胁检测和模式切换

        Args:
            nearby_entities: 附近的实体列表（字典格式）
        """
        try:
            # 检测敌对生物
            hostile_entities = []
            for entity_dict in nearby_entities:
                if isinstance(entity_dict, dict):
                    # 检查多种可能的敌对标识
                    entity_type = entity_dict.get("type", "")
                    entity_name = entity_dict.get("name", "").lower()
                    entity_kind = entity_dict.get("kind", "").lower()

                    is_hostile = (
                        entity_type == "hostile" or
                        entity_kind == "hostile" or
                        entity_name in self.hostile_entity_names or
                        any(keyword in entity_name for keyword in ["zombie", "skeleton", "creeper", "spider"])
                    )

                    if is_hostile:
                        hostile_entities.append(entity_dict)

            # 更新威胁计数
            old_threat_count = self.threat_count
            self.threat_count = len(hostile_entities)
            self.active_threats = [(entity, 0.0) for entity in hostile_entities]  # 简化处理，距离设为0

            # 模式切换逻辑 - 只在状态变化时记录日志
            if self.threat_count > 0 and not self.in_combat_mode:
                logger.info(f"[威胁检测] ⚠️ 检测到 {self.threat_count} 个威胁，进入战斗模式")
                try:
                    from agent.mai_mode import mai_mode
                    await mai_mode.set_mode("combat_mode", f"检测到 {self.threat_count} 个威胁生物", "CombatHandler")
                except Exception as e:
                    logger.error(f"切换到战斗模式失败: {e}")
            elif self.threat_count == 0 and self.in_combat_mode and self._should_exit_alert_mode():
                logger.info("[威胁检测] 🟢 威胁消除，退出战斗模式")
                try:
                    from agent.mai_mode import mai_mode
                    await mai_mode.set_mode("main_mode", "威胁消除", "CombatHandler")
                except Exception as e:
                    logger.error(f"切换回主模式失败: {e}")

            # 记录威胁信息到思考日志
            if self.threat_count > 0:
                threat_names = [f"{entity.get('name', 'unknown')}" for entity in hostile_entities[:3]]
                if len(hostile_entities) > 3:
                    threat_names.append(f"等{len(hostile_entities)}个")
                threat_list = ", ".join(threat_names)
                from agent.thinking_log import global_thinking_log
                global_thinking_log.add_thinking_log(
                    f"⚠️ 检测到威胁生物：{threat_list}",
                    type="threat_detected",
                )

        except Exception as e:
            logger.error(f"威胁检测处理失败: {e}")

    def _create_entity_from_dict(self, entity_dict: dict) -> Optional[Entity]:
        """从字典创建Entity对象"""
        try:
            from agent.common.basic_class import Entity, Position

            entity_type = entity_dict.get("type", "")
            name = entity_dict.get("name", "")
            position_data = entity_dict.get("position", {})

            if not position_data:
                return None

            position = Position(
                x=position_data.get("x", 0),
                y=position_data.get("y", 0),
                z=position_data.get("z", 0)
            )

            entity = Entity(
                type=entity_type,
                name=name,
                position=position
            )

            return entity
        except Exception as e:
            logger.debug(f"创建Entity对象失败: {e}")
            return None

    @property
    def mode_type(self) -> str:
        """实现 ModeHandler 接口"""
        return MaiModeType.COMBAT.value

    def can_enter_mode(self) -> bool:
        """检查是否可以进入战斗模式"""
        return self.detection_config.get("enabled", True)

    def can_exit_mode(self) -> bool:
        """检查是否可以退出战斗模式"""
        return True  # 战斗模式随时可以退出

    def check_transitions(self) -> List[ModeTransition]:
        """检查战斗模式的自动转换条件

        战斗模式应该在以下情况下自动退出：
        1. 没有威胁生物存在
        2. 威胁状态超时
        """
        from agent.mai_mode import ModeTransition

        transitions = []

        # 检查是否应该退出到主模式
        should_exit = (
            self.threat_count == 0 or  # 没有威胁
            self._is_threat_timeout()   # 超时
        )

        if should_exit:
            transitions.append(ModeTransition(
                target_mode="main_mode",
                priority=10,  # 高优先级，确保威胁消除时快速退出
                condition_name="threat_cleared_or_timeout"
            ))

        return transitions

    async def on_enter_mode(self, reason: str, triggered_by: str) -> None:
        """进入战斗模式"""
        logger.info(f"🔴 进入战斗模式: {reason}")
        self.in_combat_mode = True
        self.threat_start_time = time.time()

        # 启动持续攻击任务
        if not self._recovery_task or self._recovery_task.done():
            self._recovery_task = asyncio.create_task(self._continuous_attack_loop())

    async def on_exit_mode(self, reason: str, triggered_by: str) -> None:
        """退出战斗模式"""
        logger.info(f"🟢 退出战斗模式: {reason}")
        self.in_combat_mode = False
        self.threat_start_time = None

        # 取消攻击任务
        if self._recovery_task and not self._recovery_task.done():
            self._recovery_task.cancel()

        # 清理状态
        self.active_threats.clear()
        self.attack_attempts.clear()
        self.threat_count = 0

        logger.debug("战斗模式处理器状态已重置")


    def _should_exit_alert_mode(self) -> bool:
        """判断是否应该退出战斗模式"""
        # 检查是否所有威胁都在安全距离外
        for _, distance in self.active_threats:
            if distance <= self.detection_config["threat_min_distance"]:
                return False
        return True

    async def _exit_alert_mode(self):
        """退出战斗模式"""
        # 注意：这里不直接调用 set_mode，因为处理器本身就是通过模式系统调用的
        # 模式切换由调用方负责，这里只处理退出逻辑

        logger.debug("[威胁检测] 威胁消除，准备退出战斗模式")
        global_thinking_log.add_thinking_log(
            "威胁消除，准备退出战斗模式",
            type="combat_mode_deactivated",
        )

    async def _continuous_attack_loop(self):
        """持续攻击循环"""
        try:
            while (self.in_combat_mode):
                # 检查是否超时
                if self._is_threat_timeout():
                    logger.warning("[威胁检测] ⏰ 战斗状态持续超时，强制退出战斗模式")
                    await self._exit_alert_mode()
                    break

                # 执行攻击
                if self.active_threats:
                    await self._execute_attacks()

                # 检查是否仍然在战斗模式下
                if not self.in_combat_mode:
                    break

                # 等待下一次攻击
                await asyncio.sleep(self.detection_config["attack_interval"])

        except asyncio.CancelledError:
            logger.info("战斗模式攻击循环被取消")
        except Exception as e:
            logger.error(f"战斗模式攻击循环异常: {e}")

    def _is_threat_timeout(self) -> bool:
        """检查威胁是否超时"""
        if not self.threat_start_time:
            return False

        elapsed = time.time() - self.threat_start_time
        return elapsed > self.detection_config["threat_timeout"]

    async def _execute_attacks(self):
        """执行攻击逻辑"""
        try:
            current_time = time.time()

            # 检查攻击冷却
            time_since_last_attack = current_time - self.last_attack_time
            if time_since_last_attack < self.detection_config["attack_interval"]:
                return

            # 按距离排序，优先攻击最近的
            self.active_threats.sort(key=lambda x: x[1])

            attacked_count = 0
            max_attacks = min(3, len(self.active_threats))  # 每次最多攻击3个

            for mob, distance in self.active_threats[:max_attacks]:
                # 由于mob是字典，使用get方法获取name
                mob_name = mob.get('name', '威胁生物') if isinstance(mob, dict) else getattr(mob, 'name', '威胁生物')

                # 检查是否超过最大攻击次数
                if self.attack_attempts.get(mob_name, 0) >= self.detection_config["max_attack_attempts"]:
                    continue

                try:
                    # 使用kill_mob工具攻击，带重试机制
                    args = {"mob": mob_name}
                    max_retries = 2
                    call_result = None

                    for attempt in range(max_retries + 1):
                        try:
                            call_result = await global_mcp_client.call_tool_directly("kill_mob", args)
                            break  # 成功调用，跳出重试循环
                        except Exception as retry_error:
                            if attempt < max_retries:
                                logger.debug(f"攻击 {mob_name} 失败，正在重试 ({attempt + 1}/{max_retries}): {retry_error}")
                                await asyncio.sleep(0.5)  # 短暂等待后重试
                            else:
                                raise retry_error  # 达到最大重试次数，抛出异常

                    # 解析工具调用结果
                    is_success, result_content = parse_tool_result(call_result)

                    if is_success:
                        logger.info(f"[威胁检测] ✅ 成功攻击 {mob_name}")
                        attacked_count += 1
                        # 重置攻击计数
                        self.attack_attempts[mob_name] = 0
                    else:
                        logger.warning(f"[威胁检测] ⚠️ 攻击 {mob_name} 失败: {result_content}")
                        # 增加攻击失败计数
                        self.attack_attempts[mob_name] = self.attack_attempts.get(mob_name, 0) + 1

                except Exception as e:
                    logger.error(f"[威胁检测] 攻击 {mob_name} 时发生错误: {e}")
                    self.attack_attempts[mob_name] = self.attack_attempts.get(mob_name, 0) + 1

            if attacked_count > 0:
                self.last_attack_time = current_time

        except Exception as e:
            logger.error(f"执行攻击逻辑时出错: {e}")

    def get_status(self) -> Dict[str, Any]:
        """获取战斗模式状态"""
        return {
            "in_combat_mode": self.in_combat_mode,
            "threat_count": self.threat_count,
            "active_threats": [
                {
                    "name": getattr(mob, 'name', '未知'),
                    "type": getattr(mob, 'type', '未知'),
                    "distance": distance
                }
                for mob, distance in self.active_threats
            ],
            "threat_start_time": self.threat_start_time,
            "elapsed_time": time.time() - self.threat_start_time if self.threat_start_time else 0,
            "is_timeout": self._is_threat_timeout(),
            "config": self.detection_config.copy(),
            "attack_attempts": self.attack_attempts.copy(),
        }

    def update_config(self, new_config: Dict[str, Any]):
        """更新检测配置"""
        self.detection_config.update(new_config)
        logger.debug(f"更新威胁检测配置: {new_config}")

    async def force_exit_alert_mode(self, reason: str = "外部强制退出"):
        """强制退出战斗模式"""
        if self.in_combat_mode:
            await self._exit_alert_mode()
            logger.info(f"强制退出战斗模式: {reason}")

    def cleanup(self):
        """清理资源"""
        if self._recovery_task and not self._recovery_task.done():
            self._recovery_task.cancel()

        logger.debug("战斗模式处理器已清理")


# 全局战斗模式处理器实例
global_combat_handler = CombatHandler()


def get_threat_status():
    """获取威胁状态（便捷函数）"""
    return global_combat_handler.get_status()


def update_threat_config(new_config: Dict[str, Any]):
    """更新威胁配置（便捷函数）"""
    global_combat_handler.update_config(new_config)


async def force_exit_threat_mode(reason: str = "外部强制退出"):
    """强制退出威胁模式（便捷函数）"""
    await global_combat_handler.force_exit_alert_mode(reason)


def register_threat_handler():
    """手动注册威胁处理器（在程序完全启动后调用）"""
    try:
        from agent.mai_mode import mai_mode
        mai_mode.register_handler(global_combat_handler)
        mai_mode.register_environment_listener(global_combat_handler)
        logger.debug("战斗处理器已手动注册到模式系统")
    except Exception as e:
        logger.error(f"手动注册战斗处理器失败: {e}")
