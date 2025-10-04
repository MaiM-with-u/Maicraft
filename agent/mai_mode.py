"""
优化后的模式系统 - 解耦架构
支持模式常量、验证、处理器注册表、配置管理和历史记录
不再依赖事件机制，实现真正的解耦
"""

import asyncio
from typing import Dict, Any, List, Optional, Protocol, Callable, Awaitable
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import threading
from utils.logger import get_logger


class MaiModeType(Enum):
    """模式类型枚举，避免魔法字符串"""
    MAIN = "main_mode"
    COMBAT = "combat_mode"
    FURNACE_GUI = "furnace_gui"
    CHEST_GUI = "chest_gui"
    # 可以在这里添加新模式


@dataclass
class ModeConfig:
    """模式配置类"""
    name: str
    description: str
    allow_llm_decision: bool = True
    priority: int = 0  # 优先级，数字越大优先级越高
    max_duration: Optional[int] = None  # 最大持续时间（秒）
    auto_restore: bool = False  # 是否自动恢复到主模式
    restore_delay: int = 0  # 自动恢复延迟（秒）


@dataclass
class ModeTransitionRecord:
    """模式切换记录"""
    from_mode: str
    to_mode: str
    timestamp: datetime
    reason: str
    triggered_by: str


class ModeTransition:
    """模式转换定义"""
    def __init__(self, target_mode: str, priority: int = 0, condition_name: str = ""):
        self.target_mode = target_mode
        self.priority = priority  # 优先级，数字越大优先级越高
        self.condition_name = condition_name  # 条件名称，用于调试


class ModeHandler(Protocol):
    """模式处理器接口 - 参考状态机设计"""

    @property
    def mode_type(self) -> str:
        """返回处理器管理的模式类型"""
        ...

    async def on_enter_mode(self, reason: str, triggered_by: str) -> None:
        """进入模式时的回调 - 类似 StateBehavior.onStateEntered"""
        ...

    async def on_exit_mode(self, reason: str, triggered_by: str) -> None:
        """退出模式时的回调 - 类似 StateBehavior.onStateExited"""
        ...

    def can_enter_mode(self) -> bool:
        """检查是否可以进入此模式"""
        return True

    def can_exit_mode(self) -> bool:
        """检查是否可以退出此模式"""
        return True

    def get_status(self) -> Dict[str, Any]:
        """获取处理器状态"""
        return {}

    def check_transitions(self) -> List[ModeTransition]:
        """检查可能的模式转换 - 类似 shouldTransition

        返回按优先级排序的转换列表，系统会按顺序尝试执行。
        返回空列表表示当前模式应该继续保持。
        """
        return []


class ModeHandlerRegistry:
    """模式处理器注册表"""

    def __init__(self):
        self._handlers: Dict[str, ModeHandler] = {}
        self._lock = threading.RLock()

    def register_handler(self, handler: ModeHandler) -> None:
        """注册模式处理器"""
        with self._lock:
            mode_type = handler.mode_type
            if mode_type in self._handlers:
                logger = get_logger("ModeHandlerRegistry")
                logger.warning(f"模式处理器 {mode_type} 已被注册，将被替换")
            self._handlers[mode_type] = handler
            logger = get_logger("ModeHandlerRegistry")
            logger.info(f"注册模式处理器: {mode_type}")

    def unregister_handler(self, mode_type: str) -> None:
        """注销模式处理器"""
        with self._lock:
            if mode_type in self._handlers:
                del self._handlers[mode_type]
                logger = get_logger("ModeHandlerRegistry")
                logger.info(f"注销模式处理器: {mode_type}")

    def get_handler(self, mode_type: str) -> Optional[ModeHandler]:
        """获取模式处理器"""
        with self._lock:
            return self._handlers.get(mode_type)

    def get_all_handlers(self) -> Dict[str, ModeHandler]:
        """获取所有处理器"""
        with self._lock:
            return self._handlers.copy()

    async def call_enter_handler(self, mode_type: str, reason: str, triggered_by: str) -> bool:
        """调用进入模式处理器"""
        handler = self.get_handler(mode_type)
        if handler:
            try:
                if handler.can_enter_mode():
                    await handler.on_enter_mode(reason, triggered_by)
                    return True
                else:
                    logger = get_logger("ModeHandlerRegistry")
                    logger.warning(f"处理器拒绝进入模式: {mode_type}")
                    return False
            except Exception as e:
                logger = get_logger("ModeHandlerRegistry")
                logger.error(f"调用进入模式处理器失败 {mode_type}: {e}")
                return False
        return True  # 没有处理器也算成功

    async def call_exit_handler(self, mode_type: str, reason: str, triggered_by: str) -> bool:
        """调用退出模式处理器"""
        handler = self.get_handler(mode_type)
        if handler:
            try:
                if handler.can_exit_mode():
                    await handler.on_exit_mode(reason, triggered_by)
                    return True
                else:
                    logger = get_logger("ModeHandlerRegistry")
                    logger.warning(f"处理器拒绝退出模式: {mode_type}")
                    return False
            except Exception as e:
                logger = get_logger("ModeHandlerRegistry")
                logger.error(f"调用退出模式处理器失败 {mode_type}: {e}")
                return False
        return True  # 没有处理器也算成功

    async def check_auto_transitions(self, current_mode: str, mode_configs: Dict[str, ModeConfig]) -> Optional[str]:
        """检查指定模式的自动转换

        Args:
            current_mode: 当前模式
            mode_configs: 模式配置字典

        Returns:
            如果应该转换，返回目标模式，否则返回 None
        """
        current_handler = self.get_handler(current_mode)
        if not current_handler:
            return None

        # 检查处理器定义的转换
        transitions = current_handler.check_transitions()
        if not transitions:
            return None

        # 按优先级排序转换（从高到低）
        transitions.sort(key=lambda t: t.priority, reverse=True)

        # 尝试找到可行的转换目标
        for transition in transitions:
            target_mode = transition.target_mode

            # 检查目标模式是否存在
            if target_mode not in mode_configs:
                continue

            # 检查是否已经是当前模式
            if target_mode == current_mode:
                continue

            # 检查优先级（获取当前模式配置）
            current_config = mode_configs.get(current_mode)
            target_config = mode_configs[target_mode]
            if current_config and target_config:
                if (current_config.priority > target_config.priority and
                    target_mode != "main_mode"):  # main_mode 可以被任何模式切换到
                    continue

            # 返回第一个可行的转换目标
            return target_mode

        return None


class EnvironmentListener(Protocol):
    """环境监听器接口"""
    async def on_environment_updated(self, environment_data: Dict[str, Any]) -> None:
        """当环境数据更新时的回调"""
        ...


class MaiMode:
    """优化后的模式管理类 - 使用处理器注册表架构，支持环境感知"""

    # 预定义模式配置
    MODE_CONFIGS = {
        MaiModeType.MAIN.value: ModeConfig(
            name="主模式",
            description="正常的AI决策和行动模式",
            allow_llm_decision=True,
            priority=0,
        ),
        MaiModeType.COMBAT.value: ModeConfig(
            name="战斗模式",
            description="检测到威胁时自动进入战斗，完全由程序控制",
            allow_llm_decision=False,
            priority=100,
            max_duration=300,  # 5分钟
            auto_restore=True,
            restore_delay=10,
        ),
        MaiModeType.FURNACE_GUI.value: ModeConfig(
            name="熔炉界面模式",
            description="使用熔炉时的专用界面模式",
            allow_llm_decision=True,
            priority=10,
        ),
        MaiModeType.CHEST_GUI.value: ModeConfig(
            name="箱子界面模式",
            description="使用箱子时的专用界面模式",
            allow_llm_decision=True,
            priority=10,
        ),
    }

    def __init__(self):
        self.logger = get_logger("MaiMode")

        # 当前模式
        self._current_mode = MaiModeType.MAIN.value
        self._current_config = self.MODE_CONFIGS[self._current_mode]

        # 模式历史记录
        self._transition_history: List[ModeTransitionRecord] = []
        self._max_history_size = 50

        # 模式切换锁（线程安全）
        self._mode_lock = threading.RLock()

        # 处理器注册表 - 替代事件机制
        self._handler_registry = ModeHandlerRegistry()

        # 环境监听器列表
        self._environment_listeners: List[EnvironmentListener] = []
        self._environment_lock = threading.RLock()

        # 最后一次环境数据
        self._last_environment_data: Optional[Dict[str, Any]] = None

        # 模式激活时间戳
        self._mode_start_time: Optional[datetime] = None

        # 自动恢复任务
        self._auto_restore_task: Optional[asyncio.Task] = None

        self.logger.info(f"模式系统初始化完成，当前模式: {self._current_mode}")

    @property
    def mode(self) -> str:
        """获取当前模式"""
        with self._mode_lock:
            return self._current_mode

    @property
    def current_config(self) -> ModeConfig:
        """获取当前模式配置"""
        with self._mode_lock:
            return self._current_config

    @property
    def transition_history(self) -> List[ModeTransition]:
        """获取模式切换历史"""
        with self._mode_lock:
            return self._transition_history.copy()

    async def set_mode(self, new_mode: str, reason: str = "", triggered_by: str = "system") -> bool:
        """
        设置新模式

        Args:
            new_mode: 新模式名称
            reason: 切换原因
            triggered_by: 触发者

        Returns:
            bool: 是否切换成功
        """
        with self._mode_lock:
            # 验证模式是否存在
            if new_mode not in self.MODE_CONFIGS:
                self.logger.warning(f"尝试设置未知模式: {new_mode}")
                return False

            # 检查是否已经是当前模式
            if new_mode == self._current_mode:
                return True

            # 检查优先级（高优先级模式不能被低优先级模式覆盖）
            new_config = self.MODE_CONFIGS[new_mode]
            if (self._current_config.priority > new_config.priority and
                new_mode != MaiModeType.MAIN.value):
                self.logger.warning(f"无法切换模式: {new_mode} 优先级低于当前模式 {self._current_mode}")
                return False

            old_mode = self._current_mode

            # 执行模式切换
            await self._switch_mode(new_mode, reason, triggered_by)

            self.logger.info(f"模式切换成功: {old_mode} -> {new_mode} ({reason})")
            return True

    async def _switch_mode(self, new_mode: str, reason: str, triggered_by: str) -> None:
        """执行模式切换的内部逻辑"""
        old_mode = self._current_mode

        # 先调用退出旧模式的处理器
        if old_mode != new_mode:
            exit_success = await self._handler_registry.call_exit_handler(old_mode, reason, triggered_by)
            if not exit_success:
                self.logger.warning(f"退出模式处理器调用失败: {old_mode}")
                # 继续执行切换，但记录警告

        # 记录切换历史
        history_transition = ModeTransitionRecord(
            from_mode=old_mode,
            to_mode=new_mode,
            timestamp=datetime.now(),
            reason=reason,
            triggered_by=triggered_by
        )
        self._transition_history.append(history_transition)

        # 限制历史记录大小
        if len(self._transition_history) > self._max_history_size:
            self._transition_history.pop(0)

        # 更新当前模式
        self._current_mode = new_mode
        self._current_config = self.MODE_CONFIGS[new_mode]
        self._mode_start_time = datetime.now()

        # 取消之前的自动恢复任务
        if self._auto_restore_task and not self._auto_restore_task.done():
            self._auto_restore_task.cancel()

        # 设置新的自动恢复任务
        if self._current_config.auto_restore and self._current_config.restore_delay > 0:
            self._schedule_auto_restore()

        # 调用进入新模式的处理器
        if old_mode != new_mode:
            enter_success = await self._handler_registry.call_enter_handler(new_mode, reason, triggered_by)
            if not enter_success:
                self.logger.warning(f"进入模式处理器调用失败: {new_mode}")
                # 继续执行，但记录警告

    def _schedule_auto_restore(self) -> None:
        """安排自动恢复任务"""
        try:
            import asyncio

            # 检查是否有运行中的事件循环
            loop = asyncio.get_running_loop()

            async def auto_restore():
                try:
                    await asyncio.sleep(self._current_config.restore_delay)
                    if self._current_mode != MaiModeType.MAIN.value:
                        self.set_mode(MaiModeType.MAIN.value, "自动恢复", "system")
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    self.logger.error(f"自动恢复任务执行失败: {e}")

            self._auto_restore_task = loop.create_task(auto_restore())
        except RuntimeError:
            # 没有运行中的事件循环，记录警告但不创建任务
            self.logger.warning("没有运行中的事件循环，跳过自动恢复任务创建")
        except Exception as e:
            self.logger.error(f"创建自动恢复任务失败: {e}")

    async def force_restore_main_mode(self, reason: str = "强制恢复") -> bool:
        """强制恢复到主模式（忽略优先级）"""
        with self._mode_lock:
            if self._current_mode == MaiModeType.MAIN.value:
                return True

            old_mode = self._current_mode
            await self._switch_mode(MaiModeType.MAIN.value, reason, "system")

            self.logger.info(f"强制恢复到主模式: {old_mode} -> {MaiModeType.MAIN.value}")
            return True

    def is_mode_expired(self) -> bool:
        """检查当前模式是否已过期"""
        if (self._mode_start_time and self._current_config.max_duration):
            elapsed = (datetime.now() - self._mode_start_time).total_seconds()
            return elapsed > self._current_config.max_duration
        return False

    def get_mode_duration(self) -> Optional[float]:
        """获取当前模式的持续时间（秒）"""
        if self._mode_start_time:
            return (datetime.now() - self._mode_start_time).total_seconds()
        return None

    def can_use_llm_decision(self) -> bool:
        """检查是否允许LLM决策"""
        return self._current_config.allow_llm_decision

    def get_available_modes(self) -> Dict[str, ModeConfig]:
        """获取所有可用模式"""
        return self.MODE_CONFIGS.copy()

    def get_mode_info(self, mode: Optional[str] = None) -> Dict[str, Any]:
        """获取模式信息"""
        target_mode = mode or self._current_mode

        if target_mode not in self.MODE_CONFIGS:
            return {}

        config = self.MODE_CONFIGS[target_mode]
        duration = self.get_mode_duration() if target_mode == self._current_mode else None

        return {
            "mode": target_mode,
            "name": config.name,
            "description": config.description,
            "allow_llm_decision": config.allow_llm_decision,
            "priority": config.priority,
            "is_current": target_mode == self._current_mode,
            "duration": duration,
            "expired": self.is_mode_expired() if target_mode == self._current_mode else False,
        }

    def clear_history(self) -> None:
        """清空模式切换历史"""
        with self._mode_lock:
            self._transition_history.clear()
            self.logger.info("模式切换历史已清空")

    def register_handler(self, handler: ModeHandler) -> None:
        """注册模式处理器"""
        self._handler_registry.register_handler(handler)

    def unregister_handler(self, mode_type: str) -> None:
        """注销模式处理器"""
        self._handler_registry.unregister_handler(mode_type)

    def get_handler(self, mode_type: str) -> Optional[ModeHandler]:
        """获取模式处理器"""
        return self._handler_registry.get_handler(mode_type)

    def get_all_handlers(self) -> Dict[str, ModeHandler]:
        """获取所有处理器"""
        return self._handler_registry.get_all_handlers()

    def register_environment_listener(self, listener: EnvironmentListener) -> None:
        """注册环境监听器"""
        with self._environment_lock:
            if listener not in self._environment_listeners:
                self._environment_listeners.append(listener)
                self.logger.debug(f"注册环境监听器: {type(listener).__name__}")

    def unregister_environment_listener(self, listener: EnvironmentListener) -> None:
        """注销环境监听器"""
        with self._environment_lock:
            if listener in self._environment_listeners:
                self._environment_listeners.remove(listener)
                self.logger.debug(f"注销环境监听器: {type(listener).__name__}")

    async def notify_environment_updated(self, environment_data: Dict[str, Any]) -> None:
        """通知所有环境监听器环境数据已更新"""
        self._last_environment_data = environment_data

        listeners_to_notify = []
        with self._environment_lock:
            listeners_to_notify = self._environment_listeners.copy()

        # 在锁外异步通知监听器，避免阻塞
        for listener in listeners_to_notify:
            try:
                self.logger.debug(f"[模式系统] 通知监听器: {type(listener).__name__}")
                await listener.on_environment_updated(environment_data)
                self.logger.debug(f"[模式系统] 监听器 {type(listener).__name__} 处理完成")
            except Exception as e:
                self.logger.error(f"通知环境监听器失败 {type(listener).__name__}: {e}")

    def get_last_environment_data(self) -> Optional[Dict[str, Any]]:
        """获取最后一次的环境数据"""
        return self._last_environment_data

    def clear_environment_listeners(self) -> None:
        """清空所有环境监听器"""
        with self._environment_lock:
            self._environment_listeners.clear()
            self.logger.debug("已清空所有环境监听器")

    async def check_auto_transitions(self) -> bool:
        """检查当前模式的自动转换 - 可在主循环中定期调用

        Returns:
            bool: 是否发生了模式切换
        """
        target_mode = await self._handler_registry.check_auto_transitions(
            self._current_mode, self.MODE_CONFIGS
        )

        if target_mode:
            reason = f"自动转换检查触发"
            triggered_by = "auto_transition_check"
            success = await self.set_mode(target_mode, reason, triggered_by)
            if success:
                self.logger.info(f"自动模式转换: {self._current_mode} -> {target_mode}")
                return True

        return False

    def add_mode_config(self, mode_type: str, config: ModeConfig) -> None:
        """动态添加模式配置（用于扩展）"""
        with self._mode_lock:
            if mode_type in self.MODE_CONFIGS:
                self.logger.warning(f"模式配置已存在，将被覆盖: {mode_type}")
            self.MODE_CONFIGS[mode_type] = config
            self.logger.info(f"添加新模式配置: {mode_type}")

# 全局实例
mai_mode = MaiMode()
logger = get_logger("MaiMode")
logger.info(f"MaiMode 全局实例创建完成，ID: {id(mai_mode)}")

# 使用示例：
#
# # 设置模式（推荐方式）
# mai_mode.set_mode("combat_mode", "检测到敌对生物", "EnvironmentUpdater")
#
# # 检查是否允许LLM决策
# if mai_mode.can_use_llm_decision():
#     # 执行LLM决策
#     pass
#
# # 获取模式信息
# info = mai_mode.get_mode_info()
# print(f"当前模式: {info['name']} - {info['description']}")
#
# # 监听模式切换事件
# def on_mode_change(old_mode, new_mode, reason, triggered_by):
#     print(f"模式切换: {old_mode} -> {new_mode} ({reason})")
#
# mai_mode.events.on("mode_changed", on_mode_change)
#
# # 添加新模式
# from agent.mai_mode import ModeConfig
# mai_mode.add_mode_config("custom_mode", ModeConfig(
#     name="自定义模式",
#     description="用户自定义的模式",
#     allow_llm_decision=True,
#     priority=50
# ))