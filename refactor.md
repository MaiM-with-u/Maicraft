# 游戏事件管理系统重构方案

## 问题分析

### 事件数据重复存储
```
当前状态：同一份事件数据存储在3个地方
- environment.recent_events (List[Event])
- thinking_log.thinking_list (事件转为字符串，type="event") 
- chat_history.chat_history (仅聊天事件)

位置：
- agent/environment/environment_updater.py:165-170
- agent/thinking_log.py 
- agent/chat_history.py
```

### Event类设计问题
```python
# agent/common/basic_class.py 中的Event类包含过多字段
@dataclass
class Event:
    type: str
    # 20+ 个 Optional 字段，大部分对特定事件无用
    chat_text: Optional[str] = None
    kick_reason: Optional[str] = None  
    entity_name: Optional[str] = None
    # ... 更多不相关字段
```

### 硬编码的事件处理
```python
# agent/environment/environment_updater.py:165
if event.type == "chat":
    global_chat_history.add_chat_history(chat_event=event)
else:
    global_environment.add_event(event)
    global_thinking_log.add_thinking_log(thinking_log=event.__str__(),type = "event")
```

## 解决方案

### 1. 统一事件存储
创建 `GameEventStore` 类，统一管理所有事件：
```python
# agent/event_store.py (新文件)
class GameEventStore:
    def __init__(self):
        self.events: List[Event] = []
    
    def add_event(self, event: Event):
        self.events.append(event)
    
    def get_recent_events(self, limit=50) -> List[Event]:
        return self.events[-limit:]
    
    def get_ai_context(self) -> List[str]:
        # 为AI提供事件上下文信息
        return [str(event) for event in self.get_recent_events()]
    
    def get_chat_events(self) -> List[Event]:
        return [e for e in self.events if e.type == "chat"]
```

### 2. 面向对象的事件类设计
创建基类和子类结构，利用多态特性：

```python
# agent/common/basic_class.py 新的事件类结构

@dataclass
class BaseEvent:
    """事件基类，包含所有事件的公共字段"""
    type: str
    timestamp: float
    server_id: str
    player_name: str
    
    def to_context_string(self) -> str:
        """为AI提供上下文信息的字符串表示"""
        return f"[{self.type}] {self.player_name}: {self.get_description()}"
    
    def get_description(self) -> str:
        """子类实现具体的描述逻辑"""
        return f"事件类型: {self.type}"

@dataclass
class ChatEvent(BaseEvent):
    """聊天事件"""
    chat_text: str = ""
    
    def get_description(self) -> str:
        return f"说: {self.chat_text}"

@dataclass  
class PlayerEvent(BaseEvent):
    """玩家相关事件 (加入、离开、移动等)"""
    kick_reason: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    
    def get_description(self) -> str:
        if self.type == "playerJoin":
            return "加入游戏"
        elif self.type == "playerLeave":
            reason = f" 原因: {self.kick_reason}" if self.kick_reason else ""
            return f"离开游戏{reason}"
        return f"玩家事件: {self.type}"

@dataclass
class BlockEvent(BaseEvent):
    """方块相关事件 (破坏、放置)"""
    block_type: Optional[str] = None
    x: Optional[int] = None
    y: Optional[int] = None
    z: Optional[int] = None
    
    def get_description(self) -> str:
        pos = f"({self.x}, {self.y}, {self.z})" if all([self.x, self.y, self.z]) else ""
        if self.type == "blockBreak":
            return f"破坏了 {self.block_type} {pos}"
        elif self.type == "blockPlace":
            return f"放置了 {self.block_type} {pos}"
        return f"方块事件: {self.type}"

@dataclass
class ItemEvent(BaseEvent):
    """物品相关事件 (收集、掉落)"""
    item_type: Optional[str] = None
    item_count: Optional[int] = None
    
    def get_description(self) -> str:
        count = f" x{self.item_count}" if self.item_count else ""
        return f"收集了 {self.item_type}{count}"

@dataclass
class EntityEvent(BaseEvent):
    """实体相关事件 (伤害、死亡)"""
    entity_name: Optional[str] = None
    damage: Optional[float] = None
    
    def get_description(self) -> str:
        if self.type == "entity_damage":
            return f"对 {self.entity_name} 造成了 {self.damage} 伤害"
        return f"实体事件: {self.type}"

# 保持向后兼容的Event工厂类
class Event(BaseEvent):
    """Event工厂类，根据事件类型创建对应的子类实例"""
    
    def __new__(cls, **kwargs):
        event_type = kwargs.get('type', '')
        
        if event_type == "chat":
            return ChatEvent(**kwargs)
        elif event_type in ["playerJoin", "playerLeave", "playerMove"]:
            return PlayerEvent(**kwargs)
        elif event_type in ["blockBreak", "blockPlace"]:
            return BlockEvent(**kwargs)
        elif event_type in ["itemPickup", "itemDrop"]:
            return ItemEvent(**kwargs)
        elif event_type in ["entity_damage", "entity_death"]:
            return EntityEvent(**kwargs)
        else:
            # 未知事件类型，使用基类
            return BaseEvent(**kwargs)
    
    @classmethod
    def from_raw_data(cls, raw_data: dict):
        """保持现有接口兼容性"""
        # 解析raw_data的逻辑保持不变，但返回对应的子类实例
        event_data = cls._parse_raw_data(raw_data)
        return cls(**event_data)
    
    @staticmethod
    def _parse_raw_data(raw_data: dict) -> dict:
        """解析原始数据，保持现有逻辑"""
        # 这里保留现有的from_raw_data解析逻辑
        # 返回解析后的字典，供__new__方法使用
        pass
```

### 3. 修改事件处理逻辑
```python
# agent/environment/environment_updater.py 简化处理
def update_events(self):
    raw_events = self.mcp_client.query_recent_events()
    for raw_event in raw_events:
        if raw_event.get("name") not in self.ignore_event_name:
            event = Event.from_raw_data(raw_event)
            global_event_store.add_event(event)  # 统一存储
```

## 重构后的目录结构

### 新增目录结构
```
agent/
├── events/                    # 新增：事件管理系统
│   ├── __init__.py
│   ├── base_event.py          # 事件基类定义
│   ├── event_store.py         # GameEventStore 统一存储管理
│   ├── event_types.py         # 事件类型常量和验证
│   └── impl/                  # 具体事件实现目录
│       ├── __init__.py
│       └── event_impl.py       # 各种具体事件类型定义
├── common/
│   ├── __init__.py
│   ├── basic_class.py         # 保留其他基础类，移除Event类
│   └── ...
└── ...
```

### 重构前后对比

**重构前**：
```
agent/
├── common/
│   └── basic_class.py          # Event类与其他基础类混在一起
├── environment/
│   ├── environment_updater.py  # 硬编码事件处理逻辑
│   └── environment.py          # 重复存储recent_events
├── chat_history.py             # 单独存储聊天事件
├── thinking_log.py             # 重复存储事件字符串
└── ...
```

**重构后**：
```
agent/
├── events/                     # 统一的事件管理
│   ├── base_event.py           # 事件类定义
│   ├── event_store.py          # 统一存储
│   └── event_types.py          # 类型常量
├── common/
│   └── basic_class.py          # 其他基础类
├── environment/
│   ├── environment_updater.py  # 简化的事件处理
│   └── environment.py          # 从event_store获取数据
├── chat_history.py             # 从event_store获取数据
├── thinking_log.py             # 从event_store获取数据
└── ...
```

### 各模块职责划分

**events/base_event.py**
- `BaseEvent`: 事件基类，定义公共字段和方法
- `Event`: 向后兼容的工厂类，保持现有接口

**events/event_store.py**
- `GameEventStore`: 统一的事件存储和访问管理
- 提供各种查询接口（get_recent_events, get_ai_context等）
- 管理事件的生命周期和内存清理

**events/event_types.py**
- 事件类型常量定义（如CHAT_EVENT, PLAYER_JOIN等）
- 事件分类映射（玩家事件、方块事件等）
- 类型验证函数和枚举

**events/impl/event_impl.py**
- `ChatEvent`: 聊天事件实现
- `PlayerEvent`: 玩家事件实现
- `BlockEvent`: 方块事件实现
- `ItemEvent`: 物品事件实现
- `EntityEvent`: 实体事件实现

## 实施步骤

### 步骤1：创建事件系统目录结构
1. 创建 `agent/events/` 目录及其子目录
2. 在各子目录中创建 `__init__.py` 文件
3. 配置包导入关系

### 步骤2：创建事件类型和存储
1. 创建 `agent/events/base_event.py` - 事件基类
2. 创建 `agent/events/event_store.py` - 存储管理
3. 创建 `agent/events/event_types.py` - 类型定义
4. 在 `agent/__init__.py` 中创建全局 `event_store` 实例

### 步骤3：修改现有模块
1. **thinking_log.py**：
   ```python
   # 修改 get_thinking_log() 方法
   def get_thinking_log_full(self):
       result = self.thinking_list.copy()
       # 从 event_store 获取事件上下文
       result.extend(global_event_store.get_ai_context())
       return result
   ```

2. **chat_history.py**：
   ```python
   # 修改获取聊天历史的方法
   def get_chat_history(self):
       # 从 event_store 获取聊天事件
       return global_event_store.get_chat_events()
   ```

3. **environment.py**：
   ```python
   # 修改 get_all_data() 方法
   "recent_events": global_event_store.get_recent_events()
   ```

### 步骤4：清理environment_updater.py
移除重复的存储逻辑：
```python
def update_events(self):
    raw_events = self.mcp_client.query_recent_events()
    for raw_event in raw_events:
        if raw_event.get("name") not in self.ignore_event_name:
            event = Event.from_raw_data(raw_event)
            global_event_store.add_event(event)
            # 移除其他存储调用
```

### 步骤5：重构Event类系统
1. 创建 `agent/events/base_event.py` - BaseEvent基类和Event工厂类
2. 创建 `agent/events/impl/event_impl.py` - 各具体事件类型定义
3. 迁移现有的 `from_raw_data()` 解析逻辑到 `_parse_raw_data()` 方法
4. 利用多态优化事件的字符串表示和上下文生成

## 验证方法

### 功能验证
1. AI决策上下文：检查 `thinking_log.get_thinking_log_full()` 返回包含事件信息
2. 聊天历史：验证聊天事件正常显示
3. 环境数据：确认 `environment.get_all_data()` 包含 recent_events
4. WebSocket推送：验证事件数据正常推送给前端

### 数据一致性
1. 事件不重复存储
2. 所有模块获取的事件数据一致
3. 内存使用减少（无重复数据）

## 修改文件清单

**新增文件**：
- `agent/events/__init__.py`
- `agent/events/base_event.py`
- `agent/events/event_store.py`
- `agent/events/event_types.py`
- `agent/events/impl/__init__.py`
- `agent/events/impl/event_impl.py`

**修改文件**：
- `agent/common/basic_class.py` (Event类优化)
- `agent/environment/environment_updater.py` (简化事件处理)
- `agent/thinking_log.py` (从event_store获取数据)
- `agent/chat_history.py` (从event_store获取数据)  
- `agent/environment/environment.py` (更新数据源)
- `agent/__init__.py` (添加全局event_store)

## 设计优势

### 面向对象的优势
1. **类型安全**：每种事件有明确的字段定义，避免字段混乱
2. **代码组织**：相关逻辑集中在对应的事件类中
3. **易于扩展**：新增事件类型只需添加新的子类
4. **多态特性**：可以为不同事件类型提供不同的处理逻辑

### 兼容性保证
1. **向后兼容**：`Event.from_raw_data()` 接口保持不变
2. **渐进迁移**：现有代码无需修改，但会获得子类实例的好处
3. **类型检查**：`isinstance(event, Event)` 仍然有效
4. **接口一致**：所有事件都可以调用基类的方法

## 关键注意事项

1. **工厂模式**：`Event` 类作为工厂，根据事件类型返回对应子类
2. **多态利用**：利用 `get_description()` 方法的多态特性优化事件展示
3. **字段合理性**：每个子类只包含相关字段，避免冗余
4. **扩展友好**：新增事件类型只需在工厂方法中添加映射关系