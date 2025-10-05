"""
模式基础类和接口

采用面向对象设计，每个模式都是一个完整的类
包含配置、行为逻辑和状态管理
"""

from typing import Dict, Any, List, Optional, Protocol
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class ModeType(Enum):
    """模式类型枚举，避免魔法字符串"""
    MAIN = "main_mode"
    COMBAT = "combat_mode"
    FURNACE_GUI = "furnace_gui"
    CHEST_GUI = "chest_gui"
    # 可以在这里添加新模式


@dataclass
class ModeTransition:
    """模式转换定义"""
    target_mode: str
    priority: int = 0  # 优先级，数字越大优先级越高
    condition_name: str = ""  # 条件名称，用于调试


class EnvironmentListener(Protocol):
    """环境监听器接口"""
    async def on_environment_updated(self, environment_data: Dict[str, Any]) -> None:
        """当环境数据更新时的回调"""
        ...


class BaseMode(ABC):
    """模式基础类 - 每个模式都是一个完整的类

    模式分为两种主要类型：
    1. 主动决策模式 (DecisionMode): 需要LLM决策来触发，如GUI操作模式
    2. 被动响应模式 (ResponseMode): 自动触发响应环境变化，如战斗模式

    核心控制属性：
    - requires_llm_decision: 是否需要LLM参与决策
    """

    def __init__(self):
        # 基本配置
        self.name: str = "未命名模式"
        self.description: str = "模式描述"
        self.priority: int = 0  # 优先级，数字越大优先级越高
        self.max_duration: Optional[int] = None  # 最大持续时间（秒）
        self.auto_restore: bool = False  # 是否自动恢复到主模式
        self.restore_delay: int = 0  # 自动恢复延迟（秒）

        # 核心控制属性
        self.requires_llm_decision: bool = True  # 是否需要LLM参与决策

        # 运行状态
        self._is_active = False
        self._start_time: Optional[float] = None

    @property
    @abstractmethod
    def mode_type(self) -> str:
        """返回模式类型"""
        pass


    @abstractmethod
    async def activate(self, reason: str, triggered_by: str) -> None:
        """激活模式 - 进入模式时的初始化"""
        pass

    @abstractmethod
    async def deactivate(self, reason: str, triggered_by: str) -> None:
        """停用模式 - 退出模式时的清理"""
        pass

    def can_activate(self) -> bool:
        """检查是否可以激活此模式"""
        return not self._is_active

    def can_deactivate(self) -> bool:
        """检查是否可以停用此模式"""
        return self._is_active

    def get_status(self) -> Dict[str, Any]:
        """获取模式状态"""
        import time
        return {
            "mode_type": self.mode_type,
            "name": self.name,
            "description": self.description,
            "is_active": self._is_active,
            "priority": self.priority,
            "requires_llm_decision": self.requires_llm_decision,
            "duration": time.time() - self._start_time if self._start_time else 0,
            "expired": self.is_expired(),
            "mode_category": "response" if not self.requires_llm_decision else "decision",
        }

    def check_transitions(self) -> List[ModeTransition]:
        """检查可能的模式转换 - 默认实现返回空列表"""
        return []

    async def execute_cycle(self) -> None:
        """执行模式的主循环逻辑 - 默认空实现"""
        pass

    def is_expired(self) -> bool:
        """检查模式是否已过期"""
        if not self._is_active or not self._start_time or not self.max_duration:
            return False
        import time
        return time.time() - self._start_time > self.max_duration

    def _set_active(self, active: bool):
        """设置活跃状态（内部使用）"""
        import time
        self._is_active = active
        if active:
            self._start_time = time.time()
        else:
            self._start_time = None


class DecisionMode(BaseMode):
    """主动决策模式基类 - 需要LLM决策来触发的模式

    特点：
    - 由LLM决策结果触发切换
    - 需要LLM参与决策过程
    - 通常是任务导向的，如GUI操作
    - 可能有持续执行循环，也可能是一次性任务

    示例：FurnaceGUIMode（熔炉操作）, ChestGUIMode（箱子操作）
    """

    def __init__(self):
        super().__init__()
        self.requires_llm_decision = True  # 需要LLM决策


class ResponseMode(BaseMode):
    """被动响应模式基类 - 自动触发响应环境变化的模式

    特点：
    - 自动检测环境变化并触发
    - 不需要LLM参与决策，完全由程序控制
    - 通常有持续的监控和响应逻辑
    - 优先级较高，可以中断其他模式

    示例：CombatMode（自动战斗响应）
    """

    def __init__(self):
        super().__init__()
        self.requires_llm_decision = False  # 不需要LLM决策，完全自动
