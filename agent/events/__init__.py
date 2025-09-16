# Events package
from .base_event import BaseEvent, Event
from .event_store import GameEventStore

# 创建全局事件存储实例
global_event_store = GameEventStore()

__all__ = ['BaseEvent', 'Event', 'GameEventStore', 'global_event_store']
