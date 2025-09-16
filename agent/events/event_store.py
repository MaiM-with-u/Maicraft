"""
GameEventStore - 统一的事件存储和访问管理
"""
from typing import List, Optional
from .base_event import BaseEvent


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
            self.events = self.events[-self.max_events:]
    
    def get_recent_events(self, limit: int = 50) -> List[BaseEvent]:
        """获取最近的事件"""
        return self.events[-limit:] if self.events else []
    
    def get_events_by_type(self, event_type: str, limit: int = 50) -> List[BaseEvent]:
        """根据事件类型获取事件"""
        filtered_events = [e for e in self.events if e.type == event_type]
        return filtered_events[-limit:] if filtered_events else []
    
    def get_ai_context(self, limit: int = 20) -> List[str]:
        """为AI提供事件上下文信息的字符串列表"""
        recent_events = self.get_recent_events(limit)
        return [event.to_context_string() for event in recent_events]
    
    def get_events_by_player(self, player_name: str, limit: int = 50) -> List[BaseEvent]:
        """根据玩家名称获取事件"""
        player_events = [e for e in self.events if e.player_name == player_name]
        return player_events[-limit:] if player_events else []
    
    def get_event_count(self) -> int:
        """获取当前存储的事件总数"""
        return len(self.events)
    
    def get_event_stats(self) -> dict:
        """获取事件统计信息"""
        stats = {}
        for event in self.events:
            event_type = event.type
            stats[event_type] = stats.get(event_type, 0) + 1
        return stats
