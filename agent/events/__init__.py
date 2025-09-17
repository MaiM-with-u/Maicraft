# Events package
from .base_event import BaseEvent, Event
from .event_store import GameEventStore
from .event_types import SUPPORTED_EVENTS
from .event_registry import register_all_events

# 创建全局事件存储实例
global_event_store = GameEventStore()

# 注册所有事件类型（在所有模块导入完成后执行）
register_all_events()

__all__ = ['BaseEvent', 'Event', 'GameEventStore', 'global_event_store', 'SUPPORTED_EVENTS']
