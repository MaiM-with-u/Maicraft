# 事件处理器 (Event Handlers)

这个目录包含各种Minecraft事件的处理器，负责处理特定的事件逻辑，支持中断当前任务、触发紧急响应等高级功能。

## 目录结构

```
handlers/
├── __init__.py           # 处理器包初始化
├── health/               # 健康事件处理器目录
│   ├── __init__.py
│   └── health_event_handler.py
└── README.md             # 说明文档
```

## 现有处理器

### HealthEventHandler (健康事件处理器)

处理Minecraft中的健康相关事件，当生命值或饱食度过低时自动中断当前任务进行紧急处理。

#### 功能特性

- **实时健康监控**: 监听health事件，跟踪生命值和饱食度变化
- **智能中断**: 生命值≤6或饱食度≤6时触发紧急中断
- **健康警告**: 生命值≤12或饱食度≤12时发出警告
- **自动恢复**: 健康恢复正常时自动退出紧急模式

#### 配置参数

```python
HEALTH_CONFIG = {
    "critical_health_threshold": 6,    # 生命值低于此值触发紧急中断
    "low_health_threshold": 12,        # 生命值低于此值发出警告
    "critical_food_threshold": 6,      # 饱食度低于此值触发紧急中断
    "low_food_threshold": 12,          # 饱食度低于此值发出警告
    "interrupt_priority": "critical"   # 中断优先级
}
```

#### 使用方法

处理器会在系统启动时自动初始化，无需手动调用。

```python
from agent.events.handlers.health.health_event_handler import get_health_status, update_health_config

# 获取当前健康状态
status = get_health_status()
print(f"当前生命值: {status['current_health']}, 上次生命值: {status['last_health']}, 是否受到伤害: {status['has_damage']}")

# 更新配置
update_health_config({
    "critical_health_threshold": 8,  # 调整紧急阈值
    "low_health_threshold": 15       # 调整警告阈值
})
```

## 添加新的处理器

### 1. 创建处理器文件

在`handlers/`目录下创建新的处理器文件：

```python
# agent/events/handlers/your_event_handler.py

from agent.events import global_event_emitter
from agent.environment.movement import global_movement
from utils.logger import get_logger

logger = get_logger("YourEventHandler")

class YourEventHandler:
    """你的自定义事件处理器"""

    def __init__(self):
        self.setup_listeners()

    def setup_listeners(self):
        """设置事件监听器"""
        global_event_emitter.on('your_event', self.handle_your_event)

    async def handle_your_event(self, event):
        """处理你的自定义事件"""
        logger.info(f"收到事件: {event.type}")

        # 处理逻辑...

        # 如果需要中断当前任务
        if self._is_emergency_condition(event):
            global_movement.trigger_interrupt("紧急情况，需要立即处理！")

def setup_your_handlers():
    """初始化函数"""
    global your_handler
    your_handler = YourEventHandler()
```

### 2. 更新__init__.py

```python
# handlers/__init__.py
from .your_event_handler import setup_your_handlers

__all__ = ['setup_your_handlers', 'setup_health_handlers']
```

### 3. 更新主events/__init__.py

```python
# events/__init__.py
def _setup_handlers():
    from .handlers import setup_health_handlers, setup_your_handlers
    setup_health_handlers()
    setup_your_handlers()  # 添加新的处理器
```

## 设计原则

### 1. 关注点分离
- 每个处理器只负责一种类型的事件
- 避免在处理器中混杂过多逻辑

### 2. 错误隔离
- 单个处理器的异常不会影响其他处理器
- 使用try-catch包装关键逻辑

### 3. 配置化
- 重要的阈值和参数通过配置管理
- 支持运行时动态调整

### 4. 日志记录
- 重要操作都要记录日志
- 便于调试和监控

### 5. 资源管理
- 避免内存泄漏
- 合理使用异步操作

## 中断机制

处理器可以通过以下方式中断当前任务：

```python
from agent.environment.movement import global_movement

# 触发中断
global_movement.trigger_interrupt("中断原因描述")

# 检查中断状态
if global_movement.interrupt_flag:
    reason = global_movement.interrupt_reason
    # 处理中断...

# 清除中断
global_movement.clear_interrupt()
```

## 扩展建议

1. **添加更多事件处理器**: 战斗事件、环境事件、物品事件等
2. **实现智能响应**: 根据当前任务类型决定是否中断
3. **添加恢复逻辑**: 中断后自动寻找解决方案（如寻找食物、治疗）
4. **性能监控**: 统计各处理器的响应时间和成功率
5. **配置界面**: 通过API动态调整处理器参数

## 测试

每个处理器都应该有对应的单元测试：

```python
# tests/test_your_event_handler.py
import pytest
from agent.events.handlers.your_event_handler import YourEventHandler

class TestYourEventHandler:
    # 测试各种场景...
```
