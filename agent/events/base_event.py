"""
事件基类定义
"""
from typing import Dict, Any, Optional, Union, TypeVar, Generic
from typing_extensions import TypedDict
from datetime import datetime
from utils.timestamp_utils import normalize_timestamp, format_timestamp_for_display, convert_timestamp_for_datetime
from .event_registry import event_registry


# 数据包装器，支持属性访问和字典访问
class DataWrapper:
    """包装字典数据，支持属性访问语法，同时保持字典的所有功能"""

    def __init__(self, data: Dict[str, Any]):
        self._data = data

    def __getattr__(self, name: str) -> Any:
        """支持属性访问：data.message"""
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"data has no attribute '{name}'")

    def __getitem__(self, key: str) -> Any:
        """支持字典访问：data["message"]"""
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """支持字典设置：data["message"] = value"""
        self._data[key] = value

    def __contains__(self, key: str) -> bool:
        """支持in操作：key in data"""
        return key in self._data

    def get(self, key: str, default=None) -> Any:
        """支持字典get方法：data.get("message", "default")"""
        return self._data.get(key, default)

    def __repr__(self) -> str:
        return repr(self._data)


# 泛型类型变量，用于事件数据类型
T = TypeVar('T', bound=Dict[str, Any])

class BaseEvent(Generic[T]):
    """事件基类，只包含所有事件都必有的字段"""

    # 子类需要定义的事件类型，由子类设置
    EVENT_TYPE: str = "unknown"

    def __init__(self, type: str, gameTick: int, timestamp: float, data: T = None):
        """自定义初始化方法，自动处理时间戳转换"""
        self.type = type
        self.gameTick = gameTick
        self._timestamp_ms = timestamp
        # 使用DataWrapper包装数据，支持属性访问和字典访问
        raw_data = data if data is not None else {}
        self.data = DataWrapper(raw_data)  # type: ignore

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
        # 返回原始字典格式，用于序列化
        data_dict = self.data._data if isinstance(self.data, DataWrapper) else self.data
        return {
            "type": self.type,
            "gameTick": self.gameTick,
            "timestamp": self.timestamp_ms,  # 使用原始毫秒级时间戳
            "data": data_dict,
        }

    @classmethod
    def from_raw_data(cls, event_data_item: dict) -> 'BaseEvent[T]':
        """从原始数据创建事件实例（通用实现）"""
        data: T = event_data_item.get("data", {})
        return cls(
            type=cls.EVENT_TYPE,
            gameTick=event_data_item.get("gameTick", 0),
            timestamp=event_data_item.get("timestamp", 0),
            data=data
        )

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
    def from_raw_data(event_data_item: Dict[str, Any]) -> BaseEvent[Dict[str, Any]]:
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
    
