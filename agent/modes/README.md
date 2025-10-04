# Minecraft AI 模式系统

这个目录实现了Minecraft AI的**行为模式管理系统**，负责管理AI在不同场景下的行为状态和决策模式。

## 模式系统概述

模式系统是Minecraft AI的核心组件之一，用于管理AI的行为状态转换。与传统的事件驱动架构不同，模式系统采用**状态机模式**，通过统一的接口管理AI的各种行为模式。

### 核心特性

- **状态管理**: 管理AI的当前行为状态（主模式、战斗模式等）
- **智能切换**: 支持条件自动切换和手动切换
- **优先级控制**: 高优先级模式可以覆盖低优先级模式
- **LLM决策控制**: 可以控制是否允许LLM参与决策
- **超时保护**: 防止模式卡死，提供自动恢复机制

### 基本概念

- **模式 (Mode)**: AI的一种行为状态，如主模式、战斗模式
- **处理器 (Handler)**: 负责管理特定模式的逻辑
- **转换 (Transition)**: 从一个模式切换到另一个模式的规则
- **优先级 (Priority)**: 模式的优先级，数字越大优先级越高

## 目录结构

```
modes/
├── __init__.py              # 模式处理器包初始化
├── base.py                  # 模式处理器接口和基础类
├── handlers/                # 具体处理器实现
│   ├── __init__.py
│   └── combat_handler.py    # 战斗模式处理器
└── README.md                # 说明文档
```

## 当前可用模式

### 1. 主模式 (main_mode)
- **优先级**: 0
- **LLM决策**: 允许
- **描述**: 默认的AI行为模式，支持LLM决策和正常游戏活动

### 2. 战斗模式 (combat_mode)
- **优先级**: 100
- **LLM决策**: 禁止
- **描述**: 检测到敌对生物时自动激活，专注于战斗行为
- **处理器**: `CombatHandler`

### 3. 熔炉界面模式 (furnace_gui)
- **优先级**: 50
- **LLM决策**: 允许
- **描述**: 与熔炉界面交互时的专用模式

### 4. 箱子界面模式 (chest_gui)
- **优先级**: 50
- **LLM决策**: 允许
- **描述**: 与箱子界面交互时的专用模式

## 使用模式系统

### 基本操作

```python
from agent.mai_mode import mai_mode, MaiModeType

# 获取当前模式
current_mode = mai_mode.mode
print(f"当前模式: {current_mode}")

# 切换到战斗模式
await mai_mode.set_mode("combat_mode", "检测到威胁", "system")

# 检查是否允许LLM决策
if mai_mode.can_use_llm_decision():
    print("当前模式允许LLM决策")

# 获取模式状态
status = mai_mode.get_status()
```

### 与战斗处理器交互

```python
from agent.modes.handlers.combat_handler import global_combat_handler

# 获取战斗模式状态
status = global_combat_handler.get_status()
print(f"威胁数量: {status['threat_count']}")
print(f"是否在战斗模式: {status['in_combat_mode']}")

# 强制退出战斗模式
await global_combat_handler.force_exit_alert_mode("手动退出")
```

## 如何添加新模式

### 步骤1: 定义模式常量

在 `mai_mode.py` 中添加新的模式常量：

```python
class MaiModeType(Enum):
    """模式类型枚举"""
    MAIN = "main_mode"
    COMBAT = "combat_mode"
    FURNACE_GUI = "furnace_gui"
    CHEST_GUI = "chest_gui"
    MINING = "mining_mode"  # 新增的采矿模式
    # 可以在这里添加更多模式
```

### 步骤2: 添加模式配置

在 `mai_mode.py` 的 `MODE_CONFIGS` 字典中添加配置：

```python
MODE_CONFIGS = {
    # 现有配置...
    MaiModeType.MINING.value: ModeConfig(
        name="采矿模式",
        description="专注于采矿活动的模式",
        allow_llm_decision=True,  # 是否允许LLM决策
        priority=30,              # 优先级（0-100）
        max_duration=3600,        # 最大持续时间（秒）
        auto_restore=True,        # 是否自动恢复到主模式
        restore_delay=60,         # 自动恢复延迟（秒）
    ),
}
```

### 步骤3: 创建处理器类

创建新的处理器文件 `agent/modes/handlers/mining_handler.py`：

```python
import time
from typing import List, Dict, Any
from agent.modes.base import ModeHandler
from agent.mai_mode import MaiModeType, ModeTransition
from utils.logger import get_logger

logger = get_logger("MiningHandler")

class MiningHandler(ModeHandler):
    """采矿模式处理器"""

    def __init__(self):
        self.is_active = False
        self.mining_start_time = None
        self.blocks_mined = 0

    @property
    def mode_type(self) -> str:
        return MaiModeType.MINING.value

    async def on_enter_mode(self, reason: str, triggered_by: str) -> None:
        """进入采矿模式"""
        logger.info(f"⛏️ 进入采矿模式: {reason}")
        self.is_active = True
        self.mining_start_time = time.time()
        self.blocks_mined = 0

        # 启动采矿任务
        # 这里实现采矿逻辑

    async def on_exit_mode(self, reason: str, triggered_by: str) -> None:
        """退出采矿模式"""
        logger.info(f"🏁 退出采矿模式: {reason}, 共挖掘 {self.blocks_mined} 个方块")
        self.is_active = False
        self.mining_start_time = None

    def can_enter_mode(self) -> bool:
        """检查是否可以进入采矿模式"""
        return True

    def can_exit_mode(self) -> bool:
        """检查是否可以退出采矿模式"""
        return True

    def get_status(self) -> Dict[str, Any]:
        """获取采矿模式状态"""
        return {
            "is_active": self.is_active,
            "blocks_mined": self.blocks_mined,
            "mining_time": time.time() - self.mining_start_time if self.mining_start_time else 0,
        }

    def check_transitions(self) -> List[ModeTransition]:
        """检查模式转换条件"""
        transitions = []

        # 如果挖掘了足够多的方块，自动退出
        if self.blocks_mined >= 100:  # 例如：挖掘100个方块后退出
            transitions.append(ModeTransition(
                target_mode="main_mode",
                priority=5,
                condition_name="mining_complete"
            ))

        return transitions

# 全局实例
global_mining_handler = MiningHandler()
```

### 步骤4: 更新包导入

更新 `modes/handlers/__init__.py`：

```python
from .combat_handler import global_combat_handler
from .mining_handler import global_mining_handler

__all__ = [
    'global_combat_handler',
    'global_mining_handler',
]
```

更新 `modes/__init__.py`：

```python
from .handlers.combat_handler import global_combat_handler
from .handlers.mining_handler import global_mining_handler

__all__ = [
    'global_combat_handler',
    'global_mining_handler',
]
```

### 步骤5: 注册处理器

在 `mai_agent.py` 中添加注册调用：

```python
# 在initialize方法中添加
from agent.modes.handlers.mining_handler import register_mining_handler
register_mining_handler()
```

## 模式处理器架构详解

### ModeHandler 接口

所有模式处理器都必须实现 `ModeHandler` 协议：

```python
class ModeHandler(Protocol):
    """模式处理器接口"""

    @property
    def mode_type(self) -> str:
        """返回处理器管理的模式类型"""
        ...

    async def on_enter_mode(self, reason: str, triggered_by: str) -> None:
        """进入模式时的回调"""
        ...

    async def on_exit_mode(self, reason: str, triggered_by: str) -> None:
        """退出模式时的回调"""
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
        """检查可能的模式转换"""
        return []
```

### 模式配置参数

每个模式都可以配置以下参数：

```python
@dataclass
class ModeConfig:
    name: str                    # 模式显示名称
    description: str            # 模式描述
    allow_llm_decision: bool    # 是否允许LLM决策
    priority: int               # 优先级（0-100，越大优先级越高）
    max_duration: int = 300     # 最大持续时间（秒）
    auto_restore: bool = True   # 是否自动恢复到主模式
    restore_delay: int = 10     # 自动恢复延迟（秒）
```

### 模式转换机制

处理器可以通过 `check_transitions()` 方法实现智能转换：

```python
def check_transitions(self) -> List[ModeTransition]:
    """检查可能的模式转换"""
    return [
        ModeTransition(
            target_mode="main_mode",     # 目标模式
            priority=10,                 # 转换优先级
            condition_name="completed"   # 条件名称（用于调试）
        )
    ]
```

## 设计原则

### 1. 单一职责原则
每个处理器只负责一种特定的行为模式，避免功能耦合。

### 2. 接口一致性
所有处理器实现相同的接口，保证系统的可扩展性。

### 3. 状态隔离
每个处理器的状态相互独立，避免意外干扰。

### 4. 优先级管理
通过优先级控制模式切换，高优先级模式可以覆盖低优先级模式。

### 5. 错误容错
单个处理器的异常不会影响整个模式系统的正常运行。

## 与事件处理器的区别

| 特性 | 事件处理器 | 模式处理器 |
|------|-----------|-----------|
| 触发方式 | 被动监听Minecraft事件 | 主动管理AI行为状态 |
| 职责范围 | 处理特定类型事件 | 管理AI的行为模式 |
| 生命周期 | 随事件出现和消失 | 通过模式系统持续管理 |
| 耦合程度 | 与事件系统紧密耦合 | 与模式系统松耦合 |
| 存储位置 | `events/handlers/` | `modes/handlers/` |
| 状态管理 | 无状态或简单状态 | 复杂的状态管理 |

## 扩展建议

1. **增加更多专用模式**: 探索模式、建造模式、交易模式等
2. **实现模式嵌套**: 支持子模式的概念
3. **增强转换条件**: 添加基于环境、时间、任务状态的转换
4. **性能监控**: 为每个处理器添加性能统计
5. **动态配置**: 通过API实时调整模式参数
6. **模式组合**: 支持同时激活多个兼容的模式

## 测试建议

为每个新模式创建单元测试：

```python
# tests/test_mining_handler.py
import pytest
from agent.modes.handlers.mining_handler import MiningHandler

class TestMiningHandler:
    async def test_enter_exit_mode(self):
        handler = MiningHandler()

        # 测试进入模式
        await handler.on_enter_mode("test", "test")
        assert handler.is_active == True

        # 测试退出模式
        await handler.on_exit_mode("test", "test")
        assert handler.is_active == False

    def test_mode_type(self):
        handler = MiningHandler()
        assert handler.mode_type == "mining_mode"

    def test_transitions(self):
        handler = MiningHandler()
        handler.blocks_mined = 150  # 超过阈值
        transitions = handler.check_transitions()
        assert len(transitions) > 0
        assert transitions[0].target_mode == "main_mode"
```
