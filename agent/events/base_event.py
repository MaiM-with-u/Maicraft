"""
事件基类定义
"""
from typing import Dict, Any
from datetime import datetime
from utils.timestamp_utils import normalize_timestamp, format_timestamp_for_display, convert_timestamp_for_datetime
from .event_registry import event_registry
class BaseEvent:
    """事件基类，只包含所有事件都必有的字段"""

    def __init__(self, type: str, gameTick: int, timestamp: float, data: Dict[str, Any] = None):
        """自定义初始化方法，自动处理时间戳转换"""
        self.type = type
        self.gameTick = gameTick
        self._timestamp_ms = timestamp
        self.data = data if data is not None else {}

        # 自动标准化时间戳（一次性转换，提高效率）
        self._normalized_timestamp = normalize_timestamp(timestamp)

    @property
    def timestamp(self) -> float:
        """获取标准化后的秒级时间戳（自动处理毫秒转秒）"""
        return self._normalized_timestamp

    @timestamp.setter
    def timestamp(self, value: float) -> None:
        """设置时间戳（自动标准化）"""
        self._timestamp_ms = value
        self._normalized_timestamp = normalize_timestamp(value)

    @property
    def timestamp_ms(self) -> float:
        """获取原始时间戳（毫秒级，用于序列化）"""
        return self._timestamp_ms

    def get_display_time(self, format_str: str = "%H:%M:%S") -> str:
        """获取格式化的时间显示字符串"""
        return format_timestamp_for_display(self.timestamp, format_str)

    def get_datetime(self):
        """获取datetime对象（自动处理时间戳转换）"""
        return datetime.fromtimestamp(convert_timestamp_for_datetime(self.timestamp))

    def __getattr__(self, name: str) -> Any:
        """
        动态访问data字段中的属性
        
        使用方法：
        - event.username 等价于 event.data["username"]
        - event.message 等价于 event.data["message"]
        - 如果data中不存在该字段，会抛出AttributeError

        两种访问方式（不重名情况下）：
        1. event.field_name （通过__getattr__动态访问，推荐）
        2. event.data["field_name"] （直接字典访问）

        注意：
        - 此方法只处理不存在于对象本身的属性访问
        - 如果事件类定义了同名属性，会优先使用类定义的属性
        - 类型提示会丢失，IDE可能无法提供完整的智能提示
        """
        if name in self.data:
            return self.data[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def get_category(self) -> str:
        """获取事件分类，子类应该重写此方法"""
        return "unknown"

    def to_context_string(self) -> str:
        """为AI提供上下文信息的字符串表示，由子类实现"""
        return f"[{self.type}] {self.get_description()}"

    def get_description(self) -> str:
        """子类实现具体的描述逻辑"""
        return f"事件类型: {self.type}"

    def to_dict(self) -> dict:
        """转换为字典格式（使用原始时间戳）"""
        return {
            "type": self.type,
            "gameTick": self.gameTick,
            "timestamp": self.timestamp_ms,  # 使用原始毫秒级时间戳
            "data": self.data,
        }
    
    def __str__(self) -> str:
        """返回事件的字符串表示，保持与原Event类兼容"""
        return self.get_description()


class EventFactory:
    """Event工厂类，根据事件类型创建对应的子类实例"""

    @staticmethod
    def create(**kwargs) -> BaseEvent:
        """使用注册表创建对应的事件实例"""
        event_type = kwargs.get('type', '')
        event = event_registry.create_event(event_type, **kwargs)

        if event is not None:
            return event
        else:
            # 未知事件类型，使用基类
            return BaseEvent(**kwargs)

    @staticmethod
    def from_raw_data(event_data_item: Dict[str, Any]) -> BaseEvent:
        """使用注册表从原始数据创建事件"""
        event = event_registry.create_event_from_raw_data(event_data_item)

        if event is not None:
            return event

        # 未知事件类型，使用基类
        event_type = event_data_item.get("type", "")
        return BaseEvent(
            type=event_type,
            gameTick=event_data_item.get("gameTick", 0),
            timestamp=event_data_item.get("timestamp", 0),
            data=event_data_item.get("data", {})
        )
    
