# Events package
from .base_event import BaseEvent, EventFactory
from .event_store import GameEventStore
from .event_types import EventType, SUPPORTED_EVENTS
from .event_registry import register_all_events
from .impl.chat_event import ChatEvent
from .event_emitter import EventEmitter, ListenerHandle  # 新增


# 创建全局事件存储实例
global_event_store = GameEventStore()

# 创建全局事件发射器实例
global_event_emitter = EventEmitter(max_listeners=200)

# 注册所有事件类型（在所有模块导入完成后执行）
register_all_events()


def setup_event_handlers():
    """
    设置所有事件处理器

    这个函数应该在应用启动时调用，而不是在模块导入时。
    这样可以避免循环依赖问题。
    """
    from .handlers import setup_hurt_response_handlers
    setup_hurt_response_handlers()


def event_listener(event_type: str, once: bool = False):
    """
    事件监听器装饰器

    使用此装饰器可以方便地注册事件监听器函数。

    Args:
        event_type: 事件类型 (如 'chat', 'playerJoined', 'entityHurt')
        once: 是否只监听一次，默认为False

    Returns:
        装饰器函数

    Example:
        @event_listener('chat')
        async def handle_chat(event):
            username = event.data.username
            message = event.data.message
            print(f"{username}: {message}")

        @event_listener('playerJoined', once=True)
        async def welcome_player(event):
            username = event.data.username
            print(f"欢迎 {username} 加入游戏！")
    """

    def decorator(func):
        if once:
            global_event_emitter.once(event_type, func)
        else:
            global_event_emitter.on(event_type, func)
        return func

    return decorator


__all__ = [
    "BaseEvent",
    "EventFactory",
    "GameEventStore",
    "global_event_store",
    "EventType",
    "SUPPORTED_EVENTS",
    "ChatEvent",
    "EventEmitter",
    "global_event_emitter",
    "ListenerHandle",  # 新增
    "event_listener",  # 装饰器
]
