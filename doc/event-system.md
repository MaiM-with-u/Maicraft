# 🎮 Maicraft-Mai 事件系统 (Event System)

Maicraft-Mai 内置强大的事件驱动架构，能够实时响应Minecraft游戏中的各种事件，为Agent提供智能决策支持。

## 🎯 核心特性

- **实时事件监听**: 支持14种Minecraft原生事件类型
- **智能中断机制**: 紧急情况自动中断当前任务
- **AI驱动响应**: 使用LLM进行智能事件处理和决策
- **并发安全**: 基于asyncio的事件处理，支持高并发
- **模块化设计**: 事件处理器可独立开发和扩展

## 📋 支持的事件类型

| 事件类型 | 描述 | 处理器状态 |
|---------|-----|----------|
| `health` | 生命值/饱食度变化 | ✅ 已实现 (智能伤害响应) |
| `chat` | 玩家聊天消息 | ✅ 已实现 |
| `entityHurt` | 实体受伤 | ✅ 已实现 |
| `entityDead` | 实体死亡 | ✅ 已实现 |
| `playerJoined` | 玩家加入 | ✅ 已实现 |
| `playerLeft` | 玩家离开 | ✅ 已实现 |
| `itemDrop` | 物品掉落 | ✅ 已实现 |
| `breath` | 呼吸状态 | ✅ 已实现 |
| `death` | 玩家死亡 | ✅ 已实现 |
| `kicked` | 被服务器踢出 | ✅ 已实现 |
| `playerCollect` | 玩家拾取物品 | ✅ 已实现 |
| `rain` | 天气变化 | ✅ 已实现 |
| `spawn` | 玩家重生 | ✅ 已实现 |
| `spawnReset` | 重生点重置 | ✅ 已实现 |

## 🩹 智能伤害响应系统

**核心功能**：
- **自动中断**: 生命值下降时立即中断当前任务
- **智能识别**: 通过entityHurt事件和周围实体信息识别伤害来源
- **AI驱动响应**:
  - 玩家攻击 → 使用聊天进行交涉
  - 怪物攻击 → 自动反击或逃跑
  - 未知伤害 → 默认交涉策略

**响应示例**：
```
玩家攻击时: "？？？我招你惹你了？？刚建个营地你就来一下？？兄弟有事咱能聊聊不？别打啊…"
怪物攻击时: "检测到僵尸攻击，准备反击..."
```

## 🏗️ 事件系统核心组件

### 1. 基础事件架构

**BaseEvent 类**：
- 统一的事件数据结构
- 时间戳管理和格式化
- 事件序列化/反序列化
- 类型安全的属性访问

**EventFactory 工厂类**：
- 根据事件类型自动创建对应的事件实例
- 支持原始数据转换为结构化事件
- 事件验证和类型检查

**DataWrapper 数据包装器**：
- 支持 `data.message` 属性访问语法
- 兼容字典操作 `data["message"]`
- 自动转换嵌套字典为对象

### 2. 事件发射器 (EventEmitter)

**核心特性**：
- **异步事件处理**：基于asyncio的并发安全事件发射
- **监听器管理**：支持多次监听器和一次性监听器
- **错误隔离**：单个监听器异常不影响其他监听器
- **性能监控**：事件处理时间统计和监听器数量限制

**ListenerHandle 句柄管理**：
```python
# 创建监听器句柄
handle = emitter.on('chat', callback)

# 清理监听器
handle.remove()
```

### 3. 事件存储 (GameEventStore)

**存储功能**：
- **循环缓冲区**：自动清理超出限制的旧事件
- **类型过滤**：按事件类型查询历史事件
- **时间窗口查询**：获取指定时间范围内的聊天记录
- **事件统计**：提供事件计数和频率分析

**查询接口**：
```python
# 获取最近50个事件
recent_events = store.get_recent_events(50)

# 获取最近30分钟的聊天记录
chat_history = store.get_recent_chat_events(30, 20)

# 获取特定类型的事件
health_events = store.get_events_by_type('health', 10)
```

### 4. 事件类型系统 (EventType)

**枚举定义**：
```python
class EventType(Enum):
    CHAT = "chat"
    PLAYER_JOINED = "playerJoined"
    PLAYER_LEFT = "playerLeft"
    DEATH = "death"
    HEALTH = "health"
    # ... 其他14种事件类型
```

**类型验证**：自动验证事件类型有效性

### 5. 事件注册器 (EventRegistry)

**自动发现机制**：
- 扫描事件实现目录
- 动态注册事件类
- 类型映射和验证
- 插件化扩展支持

### 6. 事件监听器装饰器

**便捷的装饰器语法**：
```python
from agent.events import event_listener

@event_listener('chat')  # 普通监听器
async def handle_chat(event):
    pass

@event_listener('death', once=True)  # 一次性监听器
async def handle_death_once(event):
    pass
```

## 📁 事件处理器架构

```
agent/events/
├── base_event.py          # 基础事件类和工厂
├── event_emitter.py       # 事件发射器和监听器管理
├── event_store.py         # 事件存储和查询
├── event_types.py         # 事件类型枚举定义
├── event_registry.py      # 事件自动注册器
├── impl/                  # 具体事件实现类
│   ├── chat_event.py      # 聊天事件
│   ├── health_event.py    # 健康事件
│   ├── entity_hurt_event.py  # 实体受伤事件
│   └── ...                # 其他11种事件
└── handlers/              # 事件处理器 (业务逻辑)
    ├── health/               # 健康事件处理器目录
    │   ├── __init__.py
    │   └── health_event_handler.py    # 智能伤害响应处理器
    └── README.md
```

## 🚀 使用事件系统

### 全局实例和导入

Maicraft-Mai 提供预初始化的全局实例，方便使用：

```python
from agent.events import (
    global_event_emitter,    # 全局事件发射器
    global_event_store,      # 全局事件存储
    event_listener,          # 事件监听器装饰器
    EventFactory,           # 事件工厂
    EventType               # 事件类型枚举
)
```

### 监听事件

**装饰器方式（推荐）**：
```python
@event_listener('chat')
async def handle_chat(event):
    """处理聊天消息"""
    username = event.data.username
    message = event.data.message
    print(f"{username}: {message}")

@event_listener('health')
async def handle_health_change(event):
    """处理生命值变化"""
    health = event.data.health
    food = event.data.food if event.data.food else 0
    print(f"生命值: {health}, 饱食度: {food}")

@event_listener('entityHurt', once=True)
async def handle_single_damage(event):
    """一次性监听实体受伤事件"""
    entity = event.data.entity
    damage = event.data.damage
    print(f"实体 {entity} 受到 {damage} 点伤害")
```

**手动注册方式**：
```python
def on_player_join(event):
    """玩家加入事件处理"""
    username = event.data.username
    print(f"欢迎 {username} 加入游戏！")

# 注册监听器，返回句柄用于后续清理
handle = global_event_emitter.on('playerJoined', on_player_join)

# 清理监听器
# handle.remove()
```

### 事件数据访问

事件数据支持多种访问方式：

```python
@event_listener('chat')
async def process_chat(event):
    # 属性访问（推荐）
    username = event.data.username
    message = event.data.message

    # 字典访问
    username = event.data["username"]
    message = event.data["message"]

    # 安全访问
    position = event.data.get("position", None)

    # 时间戳访问
    timestamp = event.timestamp
    readable_time = event.get_formatted_time()
```

### 查询历史事件

使用全局事件存储查询历史数据：

```python
# 获取最近50个事件
recent_events = global_event_store.get_recent_events(50)

# 获取最近30分钟的聊天记录
chat_history = global_event_store.get_recent_chat_events(
    time_window_minutes=30,
    max_count=20
)

# 获取特定类型的事件
health_events = global_event_store.get_events_by_type('health', 10)
death_events = global_event_store.get_events_by_type('death', 5)

# 遍历事件
for event in chat_history:
    print(f"[{event.get_formatted_time()}] {event.data.username}: {event.data.message}")
```

### 触发自定义事件

```python
from agent.events import EventFactory

# 创建自定义事件
custom_event = EventFactory.from_raw_data({
    'type': 'custom_ai_action',
    'data': {
        'action': 'mining',
        'target': 'diamond_ore',
        'priority': 'high'
    }
})

# 异步发射事件
await global_event_emitter.emit(custom_event)
```

### 任务中断机制

与移动系统的集成：

```python
from agent.environment.movement import global_movement

@event_listener('health')
async def emergency_health_handler(event):
    """紧急健康处理"""
    health = event.data.health

    if health <= 6:  # 生命值过低
        # 触发中断
        global_movement.trigger_interrupt("生命值过低，紧急治疗！")

        # 执行紧急处理逻辑
        await emergency_healing()

# 检查中断状态
def check_interrupt_status():
    if global_movement.interrupt_flag:
        reason = global_movement.interrupt_reason
        print(f"任务被中断: {reason}")

        # 清理中断状态
        global_movement.clear_interrupt()
```

### 异步事件处理模式

事件系统支持完全异步的处理模式：

```python
import asyncio

@event_listener('playerJoined')
async def async_welcome(event):
    """异步欢迎新玩家"""
    username = event.data.username

    # 模拟异步操作
    await asyncio.sleep(1)

    # 发送欢迎消息
    welcome_message = f"欢迎 {username} 加入我们的世界！"
    await send_chat_message(welcome_message)

    # 记录到日志
    logger.info(f"新玩家 {username} 已欢迎")
```

### 错误处理和调试

```python
@event_listener('entityHurt')
async def handle_damage_with_error_handling(event):
    """带错误处理的伤害事件处理"""
    try:
        entity = event.data.entity
        damage = event.data.damage

        # 处理逻辑...
        await process_damage(entity, damage)

    except Exception as e:
        logger.error(f"处理伤害事件失败: {e}")
        # 错误不会影响其他监听器
```

### 性能监控和统计

```python
# 获取发射器统计信息
stats = global_event_emitter.get_stats()
print(f"监听器数量: {stats['listener_count']}")
print(f"已发射事件数: {stats['events_emitted']}")
print(f"平均处理时间: {stats['avg_processing_time']}ms")

# 获取存储统计信息
store_stats = global_event_store.get_stats()
print(f"存储事件总数: {store_stats['total_events']}")
print(f"事件类型分布: {store_stats['event_type_distribution']}")
```

## ⚙️ 配置和监控

### 配置文件结构

Maicraft-Mai 支持多级配置，事件系统相关配置：

```toml
[events]
# 全局事件系统配置
max_listeners = 200                # 最大监听器数量
enable_stats = true               # 启用统计功能
log_level = "INFO"                # 事件日志级别

[events.store]
# 事件存储配置
max_events = 500                  # 最大存储事件数量
enable_auto_cleanup = true        # 启用自动清理
cleanup_interval = 300            # 清理间隔(秒)

[events.handlers.health]
# 健康事件处理器配置
enable_damage_interrupt = true     # 启用伤害中断
critical_health_threshold = 6      # 生命值紧急阈值
low_health_threshold = 12          # 生命值警告阈值
critical_food_threshold = 6        # 饱食度紧急阈值
low_food_threshold = 12            # 饱食度警告阈值
interrupt_priority = "critical"    # 中断优先级

[events.handlers.your_custom]
# 自定义处理器配置
enable_feature_x = true
threshold_value = 10
response_delay = 2.0
```

### 运行时动态配置

支持运行时动态调整配置：

```python
from agent.events.handlers.health.health_event_handler import update_health_config

# 动态更新健康处理器配置
update_health_config({
    "critical_health_threshold": 8,    # 提高紧急阈值
    "low_health_threshold": 15,        # 提高警告阈值
    "enable_damage_interrupt": False   # 临时禁用中断
})

# 重置为默认配置
update_health_config({
    "critical_health_threshold": 6,
    "low_health_threshold": 12,
    "enable_damage_interrupt": True
})
```

### 监控和统计

**事件发射器统计**：
```python
from agent.events import global_event_emitter

# 获取实时统计信息
stats = global_event_emitter.get_stats()
print("=== 事件发射器统计 ===")
print(f"总监听器数量: {stats['total_listeners']}")
print(f"活跃监听器: {stats['active_listeners']}")
print(f"已发射事件总数: {stats['events_emitted']}")
print(f"平均处理时间: {stats['avg_processing_time']:.2f}ms")
print(f"最大处理时间: {stats['max_processing_time']:.2f}ms")
print(f"事件类型分布: {stats['event_type_distribution']}")

# 监听器详情
for listener_info in stats['listener_details']:
    print(f"监听器: {listener_info['event_type']} - {listener_info['status']}")
```

**事件存储统计**：
```python
from agent.events import global_event_store

# 获取存储统计
store_stats = global_event_store.get_stats()
print("=== 事件存储统计 ===")
print(f"存储事件总数: {store_stats['total_events']}")
print(f"存储容量使用: {store_stats['capacity_usage']:.1%}")
print(f"最旧事件时间: {store_stats['oldest_event_time']}")
print(f"最新事件时间: {store_stats['newest_event_time']}")

# 事件类型分布
print("事件类型分布:")
for event_type, count in store_stats['event_distribution'].items():
    print(f"  {event_type}: {count} 次")

# 清理统计
print(f"已清理事件数: {store_stats['cleaned_events']}")
```

### 日志和调试

**事件日志配置**：
```python
import logging

# 配置事件系统日志
event_logger = logging.getLogger('agent.events')
event_logger.setLevel(logging.DEBUG)

# 创建文件处理器
file_handler = logging.FileHandler('logs/events.log')
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
event_logger.addHandler(file_handler)
```

**调试模式**：
```python
# 启用详细事件调试
import os
os.environ['EVENT_DEBUG'] = 'true'

# 在调试模式下，事件系统会记录：
# - 每个事件的完整数据
# - 监听器执行时间
# - 错误堆栈跟踪
# - 内存使用情况
```

### 性能优化建议

1. **监听器数量控制**：
```python
# 检查监听器数量，避免过度订阅
stats = global_event_emitter.get_stats()
if stats['total_listeners'] > 100:
    logger.warning("监听器数量过多，可能影响性能")
```

2. **事件过滤**：
```python
# 在监听器中尽早过滤不需要的事件
@event_listener('chat')
async def handle_important_chat(event):
    # 尽早返回不需要处理的事件
    if not event.data.message.startswith('!'):
        return

    # 只处理命令消息
    await process_command(event.data.message)
```

3. **异步处理优化**：
```python
# 使用适当的并发控制
import asyncio
from agent.events import global_event_emitter

semaphore = asyncio.Semaphore(5)  # 限制并发数量

@global_event_emitter.on('heavy_event')
async def handle_heavy_event(event):
    async with semaphore:
        # 限制同时处理的事件数量
        await heavy_processing(event)
```

4. **内存管理**：
```python
# 定期清理旧事件
from agent.events import global_event_store

# 每小时清理一次超24小时的事件
async def cleanup_old_events():
    while True:
        await asyncio.sleep(3600)  # 1小时
        # 清理24小时前的聊天事件
        global_event_store.cleanup_events(
            event_types=['chat'],
            older_than_hours=24
        )
```

### 故障排查

**常见问题诊断**：

1. **事件未触发**：
```python
# 检查事件注册
supported_events = EventType._value2member_map_.keys()
print(f"支持的事件类型: {supported_events}")

# 检查监听器注册
stats = global_event_emitter.get_stats()
print(f"活跃监听器: {len(stats['active_listeners'])}")
```

2. **性能问题**：
```python
# 监控处理时间
stats = global_event_emitter.get_stats()
if stats['avg_processing_time'] > 100:  # 超过100ms
    logger.warning("事件处理时间过长，检查监听器逻辑")
```

3. **内存泄漏**：
```python
# 检查事件存储使用情况
store_stats = global_event_store.get_stats()
if store_stats['capacity_usage'] > 0.9:  # 使用率超过90%
    logger.warning("事件存储接近容量限制")
```

**健康检查接口**：
```python
async def health_check():
    """系统健康检查"""
    try:
        # 检查事件发射器
        emitter_stats = global_event_emitter.get_stats()

        # 检查事件存储
        store_stats = global_event_store.get_stats()

        # 检查处理器状态
        health_status = get_health_status()

        return {
            "status": "healthy",
            "event_system": {
                "listeners": emitter_stats['total_listeners'],
                "events_stored": store_stats['total_events'],
                "current_health": health_status['current_health'],
                "last_health": health_status['last_health'],
                "has_damage": health_status['has_damage']
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
```

## 🔧 扩展事件系统

事件系统采用模块化设计，支持三种扩展方式：

### 1. 添加新的具体事件实现

**步骤1：创建事件类**
```python
# agent/events/impl/your_custom_event.py
from agent.events.base_event import BaseEvent
from agent.events.event_types import EventType

class YourCustomEvent(BaseEvent):
    """自定义事件实现"""

    def __init__(self, data: dict, timestamp=None):
        super().__init__(
            type=EventType.YOUR_CUSTOM.value,  # 使用枚举值
            data=data,
            timestamp=timestamp
        )

    @classmethod
    def get_category(cls) -> str:
        """返回事件分类"""
        return "custom"

    def validate_data(self) -> bool:
        """验证事件数据"""
        required_fields = ['action', 'target']
        return all(field in self.data for field in required_fields)
```

**步骤2：注册事件类**
```python
# agent/events/impl/__init__.py
from .your_custom_event import YourCustomEvent

__all__ = ['YourCustomEvent']
```

事件注册器会自动发现并注册新的事件类。

### 2. 创建新的事件处理器

**智能事件处理器模式**：
```python
# agent/events/handlers/smart_your_handler.py
import asyncio
import logging
from typing import Optional
from agent.events import global_event_emitter, global_event_store
from agent.environment.movement import global_movement
from utils.logger import get_logger

logger = get_logger("SmartYourHandler")

class SmartYourHandler:
    """智能自定义事件处理器"""

    def __init__(self):
        self._processing_lock = asyncio.Lock()  # 并发控制
        self.setup_listeners()

    def setup_listeners(self):
        """设置事件监听器"""
        global_event_emitter.on('your_custom_event', self.handle_custom_event)
        global_event_emitter.on('related_event', self.handle_related_event)

    async def handle_custom_event(self, event):
        """处理自定义事件"""
        async with self._processing_lock:
            try:
                action = event.data.action
                target = event.data.target

                logger.info(f"处理自定义事件: {action} -> {target}")

                # 智能决策逻辑
                await self._process_smart_logic(event)

            except Exception as e:
                logger.error(f"处理自定义事件失败: {e}")

    async def _process_smart_logic(self, event):
        """智能处理逻辑"""
        # 获取相关历史事件进行决策
        recent_events = global_event_store.get_recent_events(20)
        similar_events = [e for e in recent_events if e.type == event.type]

        # 基于历史数据进行决策
        if len(similar_events) > 3:
            logger.warning("检测到频繁的自定义事件，触发保护机制")
            global_movement.trigger_interrupt("系统保护：事件过于频繁")

        # 执行具体业务逻辑
        await self._execute_business_logic(event)

    async def _execute_business_logic(self, event):
        """执行业务逻辑"""
        # 具体实现...
        pass

# 全局实例
smart_your_handler = SmartYourHandler()
```

**步骤3：集成处理器**
```python
# agent/events/handlers/__init__.py
from .smart_your_handler import smart_your_handler

__all__ = ['smart_your_handler', 'setup_health_handlers']

def setup_smart_your_handlers():
    """初始化智能自定义处理器"""
    # 处理器已在模块级别初始化
    pass
```

**步骤4：注册到主事件系统**
```python
# agent/events/__init__.py
def _setup_handlers():
    from .handlers import (
        setup_health_handlers,
        setup_smart_your_handlers
    )

    setup_health_handlers()
    setup_smart_your_handlers()
```

### 3. 扩展事件类型枚举

**添加新的事件类型**：
```python
# agent/events/event_types.py
class EventType(Enum):
    # ... 现有事件类型 ...

    # 新增自定义事件类型
    YOUR_CUSTOM = "yourCustomEvent"
    ADVANCED_AI = "advancedAIAction"
    ENVIRONMENT_CHANGE = "environmentChange"
```

### 4. 高级扩展模式

**插件化扩展**：
```python
# plugins/your_plugin/event_handler.py
from agent.events import global_event_emitter, event_listener

class PluginEventHandler:
    """插件式事件处理器"""

    def __init__(self):
        self.register_plugin_events()

    def register_plugin_events(self):
        """注册插件事件"""
        # 使用装饰器注册
        pass

    @event_listener('plugin_custom_event')
    async def handle_plugin_event(self, event):
        """处理插件事件"""
        # 插件逻辑...
        pass

# 在插件初始化时注册
def init_plugin():
    global plugin_handler
    plugin_handler = PluginEventHandler()
```

**动态事件类型注册**：
```python
# 运行时动态添加事件类型
from agent.events.event_types import EventType

# 扩展枚举（注意：Python枚举不可修改，建议预定义）
# 或者使用字符串类型事件

# 发射动态事件
dynamic_event = EventFactory.from_raw_data({
    'type': 'runtime_custom_event',
    'data': {'dynamic': True}
})
await global_event_emitter.emit(dynamic_event)
```
