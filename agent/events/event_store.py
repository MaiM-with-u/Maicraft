"""
GameEventStore - 统一的事件存储和访问管理
"""

from typing import List
from datetime import datetime
from .base_event import BaseEvent
from .event_types import EventType


class GameEventStore:
    """游戏事件统一存储管理器"""

    def __init__(self, max_events: int = 500):
        """
        初始化事件存储

        Args:
            max_events: 最大存储事件数量，超过时自动清理旧事件
        """
        self.events: List[BaseEvent] = []
        self.max_events = max_events

    def add_event(self, event: BaseEvent):
        """添加事件到存储"""
        self.events.append(event)

        # 如果超过最大数量，移除最旧的事件
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events :]

    def get_recent_events(self, limit: int = 50) -> List[BaseEvent]:
        """获取最近的事件"""
        return self.events[-limit:] if self.events else []

    def get_events_by_type(self, event_type: str, limit: int = 50) -> List[BaseEvent]:
        """根据事件类型获取事件"""
        filtered_events = [e for e in self.events if e.type == event_type]
        return filtered_events[-limit:] if filtered_events else []

    def get_game_events(self, limit: int = 50) -> List[BaseEvent]:
        """
        获取游戏相关事件（死亡、实体、物品、玩家、天气、生成等）

        Args:
            limit: 最大返回事件数量，默认为50条

        Returns:
            游戏相关事件列表
        """
        # 定义需要过滤的事件类型
        target_event_types = {
            EventType.DEATH.value,
            EventType.ENTITY_DEAD.value,
            EventType.ENTITY_HURT.value,
            EventType.ITEM_DROP.value,
            EventType.PLAYER_COLLECT.value,
            EventType.PLAYER_JOINED.value,
            EventType.PLAYER_LEFT.value,
            EventType.RAIN.value,
            EventType.SPAWN.value,
            EventType.SPAWN_RESET.value
        }

        # 过滤目标类型的事件
        game_events = [
            event for event in self.events
            if event.type in target_event_types
        ]

        # 返回最近的指定数量事件
        return game_events[-limit:] if game_events else []

    def get_recent_chat_events(
        self, time_window_minutes: int = 30, max_count: int = 30
    ) -> List[BaseEvent]:
        """
        获取最近一段时间内的聊天记录

        Args:
            time_window_minutes: 时间窗口（分钟），默认为30分钟
            max_count: 最大返回记录数，默认为30条

        Returns:
            最近的聊天事件列表
        """
        # 获取所有聊天事件
        chat_events = self.get_events_by_type(EventType.CHAT.value)

        # 过滤最近指定时间内的聊天记录
        current_time = datetime.now().timestamp()
        time_window_seconds = time_window_minutes * 60
        recent_chats = [
            chat_event
            for chat_event in chat_events
            if current_time - chat_event.timestamp <= time_window_seconds
        ]

        # 限制最多返回指定数量
        return (
            recent_chats[-max_count:] if len(recent_chats) > max_count else recent_chats
        )
