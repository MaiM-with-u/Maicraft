"""
模式处理器基础类和接口

定义了所有模式处理器的统一接口和基础功能
"""

from typing import Dict, Any, List, Protocol
from abc import ABC, abstractmethod

from agent.mai_mode import ModeTransition


class ModeHandler(Protocol):
    """模式处理器接口 - 参考状态机设计"""

    @property
    @abstractmethod
    def mode_type(self) -> str:
        """返回处理器管理的模式类型"""
        ...

    @abstractmethod
    async def on_enter_mode(self, reason: str, triggered_by: str) -> None:
        """进入模式时的回调 - 类似 StateBehavior.onStateEntered"""
        ...

    @abstractmethod
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


class BaseModeHandler(ABC):
    """模式处理器基础实现类"""

    def __init__(self):
        self._active = False

    @property
    @abstractmethod
    def mode_type(self) -> str:
        """返回处理器管理的模式类型"""
        pass

    @abstractmethod
    async def on_enter_mode(self, reason: str, triggered_by: str) -> None:
        """进入模式时的回调"""
        pass

    @abstractmethod
    async def on_exit_mode(self, reason: str, triggered_by: str) -> None:
        """退出模式时的回调"""
        pass

    @property
    def is_active(self) -> bool:
        """检查处理器是否处于活跃状态"""
        return self._active

    def can_enter_mode(self) -> bool:
        """检查是否可以进入此模式"""
        return True

    def can_exit_mode(self) -> bool:
        """检查是否可以退出此模式"""
        return True

    def get_status(self) -> Dict[str, Any]:
        """获取处理器状态"""
        return {
            "mode_type": self.mode_type,
            "is_active": self.is_active,
        }

    def check_transitions(self) -> List[ModeTransition]:
        """检查可能的模式转换 - 默认实现返回空列表"""
        return []

    def _set_active(self, active: bool):
        """设置活跃状态（内部使用）"""
        self._active = active
