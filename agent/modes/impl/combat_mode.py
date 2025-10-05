"""
战斗模式

采用面向对象设计，战斗模式是一个完整的类
包含配置、威胁检测逻辑、自动攻击行为等
"""

import asyncio
import time
from typing import List, Tuple, Optional, Dict, Any
from agent.modes.base import ResponseMode, EnvironmentListener, ModeTransition, ModeType
from agent.environment.movement import global_movement
from agent.thinking_log import global_thinking_log
from mcp_server.client import global_mcp_client
from agent.utils.utils import parse_tool_result
from agent.common.basic_class import Entity
from utils.logger import get_logger

logger = get_logger("CombatMode")


class CombatMode(ResponseMode, EnvironmentListener):
    """战斗模式 - 检测威胁并自动战斗"""

    def __init__(self):
        super().__init__()

        # 基本配置
        self.name = "战斗模式"
        self.description = "检测到威胁时自动进入战斗，完全由程序控制"
        # ResponseMode 自动设置 requires_llm_decision = False
        self.priority = 100
        self.max_duration = 300  # 5分钟
        self.auto_restore = True
        self.restore_delay = 10


        # 威胁检测配置
        self.threat_detection_distance = 16.0
        self.threat_min_distance = 8.0
        self.threat_timeout = 300  # 5分钟

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

        # 攻击配置
        self.attack_interval = 2.0  # 攻击间隔（秒）
        self.max_attack_attempts = 5  # 最大攻击尝试次数

        # 状态跟踪
        self.last_attack_time = 0
        self.attack_attempts: Dict[str, int] = {}  # 记录对每个敌人的攻击次数

        # 自动攻击任务
        self._attack_task: Optional[asyncio.Task] = None

        logger.debug("战斗模式初始化完成")

    @property
    def mode_type(self) -> str:
        """返回模式类型"""
        return ModeType.COMBAT.value

    def register_to_system(self):
        """注册模式到模式系统"""
        # 调用基类注册方法
        super().register_to_system()

        # CombatMode特殊处理：注册为环境监听器
        try:
            from agent.mai_mode import mode_manager
            mode_manager.register_environment_listener(self)
            logger.debug("战斗模式已注册为环境监听器")
        except Exception as e:
            logger.error(f"战斗模式环境监听器注册失败: {e}")

    async def on_environment_updated(self, environment_data: Dict[str, Any]) -> None:
        """实现 EnvironmentListener 接口：处理环境更新"""
        try:
            # 获取实体数据 - 支持多种数据格式
            nearby_entities = []
            if "nearby_entities" in environment_data:
                nearby_entities = environment_data["nearby_entities"]
            elif "entities" in environment_data:
                nearby_entities = environment_data["entities"]
            else:
                # 如果没有明确的实体数据，跳过处理
                return

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

            # 记录威胁状态变化
            if self.threat_count > 0 and old_threat_count == 0:
                logger.info(f"[威胁检测] ⚠️ 检测到 {self.threat_count} 个威胁")
                # 检测到新威胁时，立即切换到战斗模式
                from agent.mai_mode import mai_mode
                current_mode = mai_mode.mode
                target_mode = ModeType.COMBAT.value
                logger.debug(f"[威胁检测] 当前模式: {current_mode}, 目标模式: {target_mode}, 相等: {current_mode == target_mode}")
                if current_mode != target_mode:
                    logger.info(f"[威胁检测] 切换到战斗模式")
                    await mai_mode.set_mode(target_mode, "检测到威胁生物", "environment_listener")
                else:
                    logger.debug("[威胁检测] 已在战斗模式，无需切换")
            elif self.threat_count == 0 and old_threat_count > 0:
                logger.info("[威胁检测] 🟢 威胁消除")
                # 威胁消除时，立即退出战斗模式
                from agent.mai_mode import mai_mode
                if mai_mode.mode == ModeType.COMBAT.value:
                    await mai_mode.set_mode(ModeType.MAIN.value, "威胁消除", "environment_listener")

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
        """返回模式类型"""
        return ModeType.COMBAT.value



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
            self.is_expired()   # 超时
        )

        if should_exit:
            transitions.append(ModeTransition(
                target_mode="main_mode",
                priority=10,  # 高优先级，确保威胁消除时快速退出
                condition_name="threat_cleared_or_timeout"
            ))

        return transitions

    async def activate(self, reason: str, triggered_by: str) -> None:
        """激活战斗模式"""
        logger.info(f"🔴 激活战斗模式: {reason}")

        # 启动持续攻击任务
        if not self._attack_task or self._attack_task.done():
            self._attack_task = asyncio.create_task(self._continuous_attack_loop())

    async def deactivate(self, reason: str, triggered_by: str) -> None:
        """停用战斗模式"""
        logger.info(f"🟢 停用战斗模式: {reason}")

        # 取消攻击任务
        if self._attack_task and not self._attack_task.done():
            self._attack_task.cancel()

        # 清理状态
        self.active_threats.clear()
        self.attack_attempts.clear()
        self.threat_count = 0

        logger.debug("战斗模式状态已重置")


    def _should_exit_combat_mode(self) -> bool:
        """判断是否应该退出战斗模式"""
        # 检查是否所有威胁都在安全距离外
        for _, distance in self.active_threats:
            if distance <= self.threat_min_distance:
                return False
        return True


    async def _continuous_attack_loop(self):
        """持续攻击循环"""
        try:
            while self._is_active:
                # 检查是否超时（通过 check_transitions 处理）
                if self._is_threat_timeout():
                    logger.warning("[威胁检测] ⏰ 战斗状态持续超时")
                    # 不直接退出，等待 check_transitions 返回转换条件
                    break

                # 执行攻击
                if self.active_threats:
                    await self._execute_attacks()

                # 等待下一次攻击
                await asyncio.sleep(self.attack_interval)

        except asyncio.CancelledError:
            logger.info("战斗策略攻击循环被取消")
        except Exception as e:
            logger.error(f"战斗策略攻击循环异常: {e}")

    def _is_threat_timeout(self) -> bool:
        """检查威胁是否超时"""
        return self.is_expired()

    async def _execute_attacks(self):
        """执行攻击逻辑"""
        try:
            current_time = time.time()

            # 检查攻击冷却
            time_since_last_attack = current_time - self.last_attack_time
            if time_since_last_attack < self.attack_interval:
                return

            # 按距离排序，优先攻击最近的
            self.active_threats.sort(key=lambda x: x[1])

            attacked_count = 0
            max_attacks = min(3, len(self.active_threats))  # 每次最多攻击3个

            for mob, distance in self.active_threats[:max_attacks]:
                # 由于mob是字典，使用get方法获取name
                mob_name = mob.get('name', '威胁生物') if isinstance(mob, dict) else getattr(mob, 'name', '威胁生物')

                # 检查是否超过最大攻击次数
                if self.attack_attempts.get(mob_name, 0) >= self.max_attack_attempts:
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
        base_status = super().get_status()
        base_status.update({
            "threat_count": self.threat_count,
            "active_threats": [
                {
                    "name": getattr(mob, 'name', '未知'),
                    "type": getattr(mob, 'type', '未知'),
                    "distance": distance
                }
                for mob, distance in self.active_threats
            ],
            "attack_attempts": self.attack_attempts.copy(),
        })
        return base_status

    def update_config(self, new_config: Dict[str, Any]):
        """更新检测配置"""
        for key, value in new_config.items():
            if hasattr(self, key):
                setattr(self, key, value)
        logger.debug(f"更新威胁检测配置: {new_config}")

    def cleanup(self):
        """清理资源"""
        if self._attack_task and not self._attack_task.done():
            self._attack_task.cancel()

        logger.debug("战斗模式已清理")


# 全局战斗模式实例
combat_mode = CombatMode()


def get_threat_status():
    """获取威胁状态（便捷函数）"""
    return combat_mode.get_status()


def update_threat_config(new_config: Dict[str, Any]):
    """更新威胁配置（便捷函数）"""
    # 更新配置参数
    for key, value in new_config.items():
        if hasattr(combat_mode, key):
            setattr(combat_mode, key, value)
    logger.debug(f"更新威胁检测配置: {new_config}")


def register_combat_mode():
    """注册战斗模式到模式系统"""
    try:
        combat_mode.register_to_system()
        logger.info("✅ CombatMode注册完成")
    except Exception as e:
        logger.error(f"❌ CombatMode注册失败: {e}")
        import traceback
        logger.error(f"注册异常详情: {traceback.format_exc()}")
