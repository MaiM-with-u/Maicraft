# Minecraft AI 模式系统

这个目录实现了Minecraft AI的**行为模式管理系统**，负责管理AI在不同场景下的行为状态和决策模式。

## 模式系统概述

模式系统是Minecraft AI的核心组件之一，用于管理AI的行为状态转换。与传统的事件驱动架构不同，模式系统采用**面向对象设计**，每个模式都是一个完整的类，包含配置、行为逻辑和状态管理。

### 核心特性

- **状态管理**: 管理AI的当前行为状态（主模式、战斗模式等）
- **智能切换**: 支持条件自动切换和手动切换
- **优先级控制**: 高优先级模式可以覆盖低优先级模式
- **LLM决策控制**: 可以控制是否允许LLM参与决策
- **超时保护**: 防止模式卡死，提供自动恢复机制
- **自包含设计**: 每个模式类封装完整的配置和行为逻辑

### 基本概念

- **模式 (Mode)**: AI的一种行为状态，每个模式都是一个完整的类
- **主动决策模式 (DecisionMode)**: 需要LLM决策来触发的模式，如GUI操作模式
- **被动响应模式 (ResponseMode)**: 自动检测环境变化并触发的模式，如战斗模式
- **模式管理器 (ModeManager)**: 负责管理所有模式实例的切换
- **转换 (Transition)**: 从一个模式切换到另一个模式的规则
- **优先级 (Priority)**: 模式的优先级，数字越大优先级越高

### 模式类型对比

| 特性 | 主动决策模式 | 被动响应模式 |
|------|-------------|-------------|
| 触发方式 | LLM决策结果 | 环境变化检测 |
| 决策需求 | 需要LLM参与 | 完全自动控制 |
| 执行特点 | 可能持续也可能一次性 | 通常有持续监控 |
| 响应速度 | 有决策延迟 | 立即自动响应 |
| 示例 | 熔炉GUI、箱子GUI | 战斗模式 |

### 主动决策 vs 被动响应

| 特性 | 主动决策模式 | 被动响应模式 |
|------|-------------|-------------|
| 触发方式 | LLM决策结果 | 环境检测 |
| 决策需求 | 需要LLM | 不需要LLM（自动推导） |
| 响应速度 | 有延迟 | 立即响应 |
| 优先级 | 普通优先级 | 可中断任何模式 |
| 示例 | 主模式、GUI操作 | 战斗模式 |

## 目录结构

```
modes/
├── __init__.py              # 模式包初始化
├── base.py                  # 模式基础类和接口
├── handlers/                # 具体模式实现
│   ├── __init__.py
│   └── combat_mode.py       # 战斗模式实现
└── README.md                # 说明文档
```

## 当前可用模式

### 1. 主模式 (main_mode)
- **优先级**: 0
- **LLM决策**: 允许
- **描述**: 默认的AI行为模式，支持LLM决策和正常游戏活动

### 2. 战斗模式 (combat_mode)
- **类型**: 行为模式
- **优先级**: 100
- **LLM决策**: 禁止
- **描述**: 检测到敌对生物时自动激活，专注于战斗行为
- **实现**: `CombatMode` (继承自 `ResponseMode`)

### 3. 熔炉界面模式 (furnace_gui)
- **类型**: 主动决策模式
- **优先级**: 50
- **LLM决策**: 允许
- **描述**: 执行熔炉冶炼任务的模式

### 4. 箱子界面模式 (chest_gui)
- **类型**: 主动决策模式
- **优先级**: 50
- **LLM决策**: 允许
- **描述**: 执行箱子物品存取任务的模式

## 使用模式系统

### 基本操作

```python
from agent.mai_mode import mode_manager

# 获取当前模式
current_mode = mode_manager.mode
print(f"当前模式: {current_mode}")

# 切换到战斗模式
await mode_manager.set_mode("combat_mode", "检测到威胁", "system")

# 检查是否允许LLM决策
if mode_manager.can_use_llm_decision():
    print("当前模式允许LLM决策")

# 获取模式状态
status = mode_manager.get_mode_info()
```

### 与战斗模式交互

```python
from agent.modes.impl.combat_mode import combat_mode

# 获取战斗模式状态
status = combat_mode.get_status()
print(f"威胁数量: {status['threat_count']}")
print(f"模式是否激活: {status['is_active']}")

# 模式的状态由模式管理器控制，无需手动激活/停用
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
        requires_llm_decision=True,  # 是否需要LLM参与决策
        priority=30,              # 优先级（0-100）
        max_duration=3600,        # 最大持续时间（秒）
        auto_restore=True,        # 是否自动恢复到主模式
        restore_delay=60,         # 自动恢复延迟（秒）
    ),
}
```

### 步骤3: 创建模式类

#### 创建主动决策模式示例 (MiningMode)

创建新的主动决策模式文件 `agent/modes/handlers/mining_mode.py`：

```python
import time
from typing import List, Dict, Any
from agent.modes.base import DecisionMode, ModeTransition, ModeType
from utils.logger import get_logger

logger = get_logger("MiningMode")

class MiningMode(DecisionMode):
    """采矿模式 - 持续采矿的模式"""

    def __init__(self):
        super().__init__()

        # 基本配置
        self.name = "采矿模式"
        self.description = "专注于采矿活动的主动决策模式"
        # DecisionMode 默认为 requires_llm_decision = True
        self.priority = 30
        self.max_duration = 3600  # 1小时
        self.auto_restore = True
        self.restore_delay = 60

        # 采矿相关状态
        self.blocks_mined = 0

    @property
    def mode_type(self) -> str:
        return ModeType.MINING.value

    async def activate(self, reason: str, triggered_by: str) -> None:
        """激活采矿模式"""
        logger.info(f"⛏️ 激活采矿模式: {reason}")
        self.blocks_mined = 0

    async def deactivate(self, reason: str, triggered_by: str) -> None:
        """停用采矿模式"""
        logger.info(f"🏁 停用采矿模式: {reason}, 共挖掘 {self.blocks_mined} 个方块")

    def get_status(self) -> Dict[str, Any]:
        """获取采矿模式状态"""
        base_status = super().get_status()
        base_status.update({
            "blocks_mined": self.blocks_mined,
        })
        return base_status

    def check_transitions(self) -> List[ModeTransition]:
        """检查模式转换条件"""
        transitions = []

        # 如果挖掘了足够多的方块，自动退出
        if self.blocks_mined >= 100:
            transitions.append(ModeTransition(
                target_mode="main_mode",
                priority=5,
                condition_name="mining_complete"
            ))

        return transitions

    async def execute_cycle(self) -> None:
        """执行采矿循环"""
        # 这里实现持续的采矿逻辑
        # 比如：寻找矿石、挖掘、移动等
        pass

# 全局实例
mining_mode = MiningMode()
```

#### 创建主动决策模式示例 (FurnaceGUIMode)

创建主动决策模式文件 `agent/modes/handlers/furnace_gui_mode.py`：

```python
from typing import Dict, Any
from agent.modes.base import DecisionMode, ModeType
from agent.sim_gui.furnace import FurnaceSimGui
from agent.common.basic_class import BlockPosition
from utils.logger import get_logger

logger = get_logger("FurnaceGUIMode")

class FurnaceGUIMode(DecisionMode):
    """熔炉GUI主动决策模式 - 执行熔炉操作任务"""

    def __init__(self, position: BlockPosition):
        super().__init__()

        # 基本配置
        self.name = "熔炉操作模式"
        self.description = f"执行熔炉操作任务 - 位置: {position.x},{position.y},{position.z}"
        # DecisionMode 默认为 requires_llm_decision = True
        self.priority = 50
        self.max_duration = 300  # 5分钟超时

        # 任务相关状态
        self.position = position
        self.furnace_gui = None

    @property
    def mode_type(self) -> str:
        return f"{ModeType.FURNACE_GUI.value}_{self.position.x}_{self.position.y}_{self.position.z}"

    async def activate(self, reason: str, triggered_by: str) -> None:
        """激活熔炉操作任务"""
        logger.info(f"🔥 激活熔炉操作任务: {self.position.x},{self.position.y},{self.position.z}")
        self.furnace_gui = FurnaceSimGui(self.position, llm_client)  # 需要传入llm_client

    async def deactivate(self, reason: str, triggered_by: str) -> None:
        """完成熔炉操作任务"""
        logger.info(f"✅ 完成熔炉操作任务: {self.position.x},{self.position.y},{self.position.z}")
        # 任务完成后自动清理

    async def execute_task(self) -> None:
        """执行熔炉操作任务"""
        if self.furnace_gui:
            result = await self.furnace_gui.furnace_gui()
            # 任务完成后，模式管理器会检测到任务完成并退出模式
            return result

# 使用示例
# position = BlockPosition(x=100, y=64, z=200)
# furnace_mode = FurnaceGUIMode(position)
# mode_manager.register_mode(furnace_mode)
```

### 步骤4: 注册模式

在模式管理器中注册模式实例：

```python
from agent.mai_mode import mode_manager
from .mining_mode import mining_mode

# 在模式初始化时注册
mode_manager.register_mode(mining_mode)
```

### 步骤5: 更新包导入

更新 `modes/handlers/__init__.py`：

```python
from .combat_mode import combat_mode
from .mining_mode import mining_mode

__all__ = [
    'combat_mode',
    'mining_mode',
]
```

更新 `modes/__init__.py`：

```python
from .impl.combat_mode import combat_mode
from .handlers.mining_mode import mining_mode

__all__ = [
    'combat_mode',
    'mining_mode',
]
```

## 模式架构详解

### 模式分类

模式系统将模式分为两种主要类型：

1. **主动决策模式 (DecisionMode)**:
   - 继承自 `DecisionMode` 基类
   - 由LLM决策结果触发，允许LLM参与
   - 执行特点可变（持续或一次性），取决于具体任务
   - 示例：采矿模式（持续采矿）、熔炉GUI（冶炼任务）

2. **被动响应模式 (ResponseMode)**:
   - 继承自 `ResponseMode` 基类
   - 自动检测环境变化并触发，完全由程序控制
   - 通常有持续监控和立即响应能力
   - 示例：战斗模式（自动战斗响应）

### BaseMode 类

所有模式都继承自 `BaseMode` 抽象基类：

```python
class BaseMode(ABC):
    """模式基础类 - 每个模式都是一个完整的类"""

    def __init__(self):
        # 基本配置
        self.name: str = "未命名模式"
        self.description: str = "模式描述"
        self.requires_llm_decision: bool = True
        self.priority: int = 0  # 优先级，数字越大优先级越高
        self.max_duration: Optional[int] = None  # 最大持续时间（秒）
        self.auto_restore: bool = False  # 是否自动恢复到主模式
        self.restore_delay: int = 0  # 自动恢复延迟（秒）

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
        }
```

### 模式管理器

模式管理器负责管理所有模式实例：

```python
class ModeManager:
    """模式管理器 - 管理所有模式实例的切换"""

    def register_mode(self, mode: BaseMode) -> None:
        """注册模式实例"""

    async def set_mode(self, new_mode_type: str, reason: str = "", triggered_by: str = "system") -> bool:
        """设置新模式"""

    def get_mode(self, mode_type: str) -> Optional[BaseMode]:
        """获取模式实例"""
```

### 模式配置参数

每个模式都可以配置以下参数：

```python
@dataclass
class ModeConfig:
    name: str                    # 模式显示名称
    description: str            # 模式描述
    requires_llm_decision: bool    # 是否需要LLM参与决策
    priority: int               # 优先级（0-100，越大优先级越高）
    max_duration: int = 300     # 最大持续时间（秒）
    auto_restore: bool = True   # 是否自动恢复到主模式
    restore_delay: int = 10     # 自动恢复延迟（秒）
```

### 策略转换机制

策略可以通过 `check_transitions()` 方法主动提出转换请求：

```python
def check_transitions(self) -> List[ModeTransition]:
    """检查策略的转换条件"""
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
每个模式只负责一种特定的行为或任务，所有相关逻辑都封装在模式类中。

### 2. 分类清晰原则
明确区分主动决策模式（需要LLM决策）和被动响应模式（自动触发），便于理解和维护。

### 3. 自包含设计
每个模式类封装完整的配置、行为逻辑和状态管理，无需外部依赖。

### 4. 单一来源原则
核心控制属性 `requires_llm_decision` 直接定义模式特征，其他相关属性通过它自动推导，避免重复设置和潜在不一致。

### 5. 优先级管理
通过优先级控制模式切换，高优先级模式可以覆盖低优先级模式。

### 6. 错误容错
单个模式的异常不会影响整个模式系统的正常运行。

## 与事件处理器的区别

| 特性 | 事件处理器 | 主动决策模式 | 被动响应模式 |
|------|-----------|-------------|-------------|
| 触发方式 | 被动监听事件 | LLM决策结果 | 环境变化检测 |
| 职责范围 | 处理特定事件 | 封装决策驱动的逻辑 | 封装自动响应的逻辑 |
| 生命周期 | 事件触发时存在 | 任务导向（可变） | 持续监控（自动） |
| 执行方式 | 同步响应 | 决策后执行 | 异步自动执行 |
| 耦合程度 | 与事件系统耦合 | 与模式系统松耦合 | 与模式系统松耦合 |
| 存储位置 | `events/handlers/` | `modes/handlers/` | `modes/handlers/` |
| 状态管理 | 无状态或简单 | 中等状态管理 | 复杂状态管理 |
| 决策能力 | 无决策权 | LLM决策驱动 | 完全自动控制 |
| 配置方式 | 无配置 | 自包含配置 | 自包含配置 |
| 示例 | 受伤事件处理 | 熔炉GUI（主动决策） | 战斗模式（被动响应） |

## 扩展建议

1. **增加更多专用模式**: 探索模式、建造模式、交易模式等
2. **实现模式嵌套**: 支持子模式的概念
3. **增强转换条件**: 添加基于环境、时间、任务状态的转换
4. **性能监控**: 为每个处理器添加性能统计
5. **动态配置**: 通过API实时调整模式参数
6. **模式组合**: 支持同时激活多个兼容的模式

## 测试建议

为每个新策略创建单元测试：

```python
# tests/test_mining_strategy.py
import pytest
from agent.modes.impl.mining_strategy import MiningStrategy

class TestMiningStrategy:
    async def test_activate_deactivate(self):
        strategy = MiningStrategy()

        # 测试激活策略
        await strategy.activate("test", "test")
        assert strategy.is_active == True

        # 测试停用策略
        await strategy.deactivate("test", "test")
        assert strategy.is_active == False

    def test_mode_type(self):
        strategy = MiningStrategy()
        assert strategy.mode_type == "mining_mode"

    def test_transitions(self):
        strategy = MiningStrategy()
        strategy.blocks_mined = 150  # 超过阈值
        transitions = strategy.check_transitions()
        assert len(transitions) > 0
        assert transitions[0].target_mode == "main_mode"
```
