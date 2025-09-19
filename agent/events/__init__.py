# Events package
from .base_event import BaseEvent, EventFactory
from .event_store import GameEventStore
from .event_types import EventType, SUPPORTED_EVENTS
from .event_registry import register_all_events
from .impl.chat_event import ChatEvent

# 创建全局事件存储实例
global_event_store = GameEventStore()

# 注册所有事件类型（在所有模块导入完成后执行）
register_all_events()

__all__ = ['BaseEvent', 'EventFactory', 'GameEventStore', 'global_event_store', 'EventType', 'SUPPORTED_EVENTS', 'ChatEvent']
