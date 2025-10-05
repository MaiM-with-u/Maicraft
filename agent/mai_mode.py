"""
模式管理系统

简洁的面向对象设计，每个模式都是一个完整的类
包含配置、行为逻辑和状态管理
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from utils.logger import get_logger
from agent.modes.base import BaseMode, EnvironmentListener, ModeTransition, ModeType


class ModeTransitionRecord:
    """模式切换记录"""
    def __init__(self, from_mode: str, to_mode: str, timestamp: datetime, reason: str, triggered_by: str):
        self.from_mode = from_mode
        self.to_mode = to_mode
        self.timestamp = timestamp
        self.reason = reason
        self.triggered_by = triggered_by


class ModeManager:
    """模式管理器 - 管理所有模式实例的切换"""

    def __init__(self):
        self.logger = get_logger("ModeManager")

        # 模式实例字典
        self._modes: Dict[str, BaseMode] = {}

        # 当前模式
        self._current_mode: Optional[BaseMode] = None

        # 模式历史记录
        self._transition_history: List[ModeTransitionRecord] = []
        self._max_history_size = 50

        # 环境监听器列表
        self._environment_listeners: List[EnvironmentListener] = []

        # 最后一次环境数据
        self._last_environment_data: Optional[Dict[str, Any]] = None

        # 自动恢复任务
        self._auto_restore_task: Optional[asyncio.Task] = None

        self.logger.info("模式管理器初始化完成")

    def register_mode(self, mode: BaseMode) -> None:
        """注册模式实例"""
        mode_type = mode.mode_type
        if mode_type in self._modes:
            self.logger.warning(f"模式 '{mode_type}' 已被注册，将被替换")
        self._modes[mode_type] = mode
        self.logger.info(f"注册模式: {mode_type} - {mode.name}")

    async def auto_register_modes(self) -> None:
        """
        自动注册所有模式类

        通过检查类继承关系自动发现并注册所有BaseMode的子类，
        无需手动维护注册列表。
        """
        import importlib
        import inspect
        import os
        from agent.modes.base import BaseMode

        self.logger.info("开始自动注册模式...")

        # 扫描modes/impl目录下的所有模块
        modes_dir = "agent.modes.impl"
        mode_count = 0

        try:
            # 获取所有Python文件
            impl_dir = os.path.join(os.path.dirname(__file__), "modes", "impl")

            for filename in os.listdir(impl_dir):
                if not filename.endswith(".py") or filename.startswith("__"):
                    continue

                module_name = filename[:-3]  # 移除.py扩展名
                module_path = f"{modes_dir}.{module_name}"

                try:
                    # 动态导入模块
                    module = importlib.import_module(module_path)

                    # 扫描模块中的所有类
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        # 检查是否是BaseMode的子类，但不是BaseMode本身
                        if (issubclass(obj, BaseMode) and obj != BaseMode and
                            obj.__module__ == module_path):

                            try:
                                # 直接调用BaseMode的标准注册方法
                                mode_instance = obj()
                                mode_instance.register_to_system()
                                mode_count += 1
                                self.logger.info(f"✓ 自动注册模式: {name} ({mode_instance.mode_type})")

                            except Exception as e:
                                self.logger.error(f"✗ 注册模式失败 {name}: {e}")
                                continue

                except Exception as e:
                    self.logger.error(f"加载模式模块失败 {module_name}: {e}")
                    continue

            self.logger.info(f"模式自动注册完成，共注册 {mode_count} 个模式")

        except Exception as e:
            self.logger.error(f"自动注册模式过程中发生错误: {e}")
            raise

    def get_mode(self, mode_type: str) -> Optional[BaseMode]:
        """获取模式实例"""
        return self._modes.get(mode_type)

    def get_all_modes(self) -> Dict[str, BaseMode]:
        """获取所有模式"""
        return self._modes.copy()

    @property
    def mode(self) -> str:
        """获取当前模式类型"""
        return self._current_mode.mode_type if self._current_mode else ""

    @property
    def current_mode(self) -> Optional[BaseMode]:
        """获取当前模式实例"""
        return self._current_mode

    @property
    def transition_history(self) -> List[ModeTransitionRecord]:
        """获取模式切换历史"""
        return self._transition_history.copy()

    async def set_mode(self, new_mode_type: str, reason: str = "", triggered_by: str = "system") -> bool:
        """设置新模式"""
        # 获取目标模式实例
        new_mode = self._modes.get(new_mode_type)
        if not new_mode:
            self.logger.warning(f"尝试设置未知模式: {new_mode_type}")
            return False

        # 检查是否已经是当前模式
        if self._current_mode and self._current_mode.mode_type == new_mode_type:
            return True

        # 检查优先级 - 被动响应模式（不需要LLM决策）可以中断任何模式
        if not new_mode.requires_llm_decision:
            # 被动响应模式（类似系统中断）可以中断任何模式
            pass
        elif self._current_mode and self._current_mode.priority > new_mode.priority and new_mode_type != ModeType.MAIN.value:
            self.logger.warning(f"无法切换模式: {new_mode_type} 优先级低于当前模式 {self._current_mode.mode_type}")
            return False

        old_mode = self._current_mode

        # 执行模式切换
        await self._switch_mode(new_mode, reason, triggered_by)
        self.logger.info(f"模式切换成功: {old_mode.mode_type if old_mode else 'None'} -> {new_mode_type} ({reason})")
        return True

    async def _switch_mode(self, new_mode: BaseMode, reason: str, triggered_by: str) -> None:
        """执行模式切换的内部逻辑"""
        old_mode_type = self._current_mode.mode_type if self._current_mode else ""

        # 停用当前模式
        if self._current_mode:
            try:
                await self._current_mode.deactivate(reason, triggered_by)
                self._current_mode._set_active(False)
            except Exception as e:
                self.logger.warning(f"停用模式失败 {old_mode_type}: {e}")

        # 记录切换历史
        history_record = ModeTransitionRecord(
            from_mode=old_mode_type,
            to_mode=new_mode.mode_type,
            timestamp=datetime.now(),
            reason=reason,
            triggered_by=triggered_by
        )
        self._transition_history.append(history_record)

        # 限制历史记录大小
        if len(self._transition_history) > self._max_history_size:
            self._transition_history.pop(0)

        # 设置新模式为当前模式
        self._current_mode = new_mode

        # 激活新模式
        try:
            await new_mode.activate(reason, triggered_by)
            new_mode._set_active(True)
        except Exception as e:
            self.logger.warning(f"激活模式失败 {new_mode.mode_type}: {e}")

        # 处理自动恢复
        await self._schedule_auto_restore()

    async def _schedule_auto_restore(self) -> None:
        """安排自动恢复任务"""
        # 取消之前的自动恢复任务
        if self._auto_restore_task and not self._auto_restore_task.done():
            self._auto_restore_task.cancel()

        # 如果当前模式需要自动恢复，创建新任务
        if self._current_mode and self._current_mode.auto_restore and self._current_mode.restore_delay > 0:
            try:
                async def auto_restore():
                    try:
                        await asyncio.sleep(self._current_mode.restore_delay)
                        if self._current_mode and self._current_mode.mode_type != ModeType.MAIN.value:
                            await self.set_mode(ModeType.MAIN.value, "自动恢复", "system")
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        self.logger.error(f"自动恢复任务执行失败: {e}")

                self._auto_restore_task = asyncio.create_task(auto_restore())
            except Exception as e:
                self.logger.error(f"创建自动恢复任务失败: {e}")

    async def force_restore_main_mode(self, reason: str = "强制恢复") -> bool:
        """强制恢复到主模式"""
        return await self.set_mode(ModeType.MAIN.value, reason, "system")

    def can_use_llm_decision(self) -> bool:
        """检查是否允许LLM决策"""
        return self._current_mode.requires_llm_decision if self._current_mode else True

    def get_available_modes(self) -> Dict[str, Dict[str, Any]]:
        """获取所有可用模式的配置信息"""
        return {mode_type: mode.get_status() for mode_type, mode in self._modes.items()}

    def get_mode_info(self, mode_type: Optional[str] = None) -> Dict[str, Any]:
        """获取模式信息"""
        target_mode = self.get_mode(mode_type) if mode_type else self._current_mode
        if not target_mode:
            return {}

        info = target_mode.get_status()
        info["is_current"] = target_mode == self._current_mode
        return info

    def clear_history(self) -> None:
        """清空模式切换历史"""
        self._transition_history.clear()
        self.logger.info("模式切换历史已清空")

    # 环境监听器管理
    def register_environment_listener(self, listener: EnvironmentListener) -> None:
        """注册环境监听器"""
        if listener not in self._environment_listeners:
            self._environment_listeners.append(listener)
            self.logger.debug(f"注册环境监听器: {type(listener).__name__}")

    def unregister_environment_listener(self, listener: EnvironmentListener) -> None:
        """注销环境监听器"""
        if listener in self._environment_listeners:
            self._environment_listeners.remove(listener)
            self.logger.debug(f"注销环境监听器: {type(listener).__name__}")

    async def notify_environment_updated(self, environment_data: Dict[str, Any]) -> None:
        """通知所有环境监听器环境数据已更新"""
        self._last_environment_data = environment_data

        listeners_to_notify = self._environment_listeners.copy()

        # 异步通知监听器，避免阻塞
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
        self._environment_listeners.clear()
        self.logger.debug("已清空所有环境监听器")

    async def check_auto_transitions(self) -> bool:
        """检查当前模式的自动转换"""
        if not self._current_mode:
            return False

        transitions = self._current_mode.check_transitions()
        if not transitions:
            return False

        # 按优先级排序转换
        transitions.sort(key=lambda t: t.priority, reverse=True)

        # 尝试找到可行的转换目标
        for transition in transitions:
            target_mode = self.get_mode(transition.target_mode)
            if not target_mode:
                continue

            # 检查是否已经是当前模式
            if target_mode == self._current_mode:
                continue

            # 检查优先级
            if self._current_mode.priority > target_mode.priority and transition.target_mode != ModeType.MAIN.value:
                continue

            # 执行转换
            reason = f"自动转换检查触发 ({transition.condition_name})"
            success = await self.set_mode(transition.target_mode, reason, "auto_transition_check")
            if success:
                self.logger.info(f"自动模式转换: {self._current_mode.mode_type} -> {transition.target_mode}")
                return True

        return False


# 全局模式管理器实例
mode_manager = ModeManager()

