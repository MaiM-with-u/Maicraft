"""
下雨事件实现
"""
from typing_extensions import TypedDict
from ..base_event import BaseEvent
from ..event_types import EventType


class RainEventData(TypedDict):
    weather: str  # thunder, rain, clear
    isRaining: bool
    thunderState: float  # 0到1之间的数值


class RainEvent(BaseEvent[RainEventData]):
    """下雨事件"""

    EVENT_TYPE = EventType.RAIN.value

    def __init__(self, type: str, gameTick: int, timestamp: float, data: RainEventData = None):
        """初始化下雨事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        """获取天气事件的描述信息"""
        weather = self.data.weather
        is_raining = self.data.isRaining
        thunder_state = self.data.thunderState

        if weather == "clear":
            return "天气转晴了"
        elif weather == "rain":
            return "开始下雨了" if is_raining else "雨停了"
        elif weather == "thunder":
            if thunder_state > 0.5:
                return "雷雨交加"
            elif is_raining:
                return "开始打雷下雨了"
            else:
                return "雷声轰鸣"
        else:
            return f"天气变化: {weather}"

    def to_context_string(self) -> str:
        """转换为上下文字符串，用于AI理解"""
        weather = self.data.weather
        is_raining = self.data.isRaining
        thunder_state = self.data.thunderState

        if weather == "clear":
            return "[weather] 天气转晴"
        elif weather == "rain":
            return "[weather] 开始下雨" if is_raining else "[weather] 雨停了"
        elif weather == "thunder":
            if thunder_state > 0.5:
                return f"[weather] 雷雨交加 (雷电强度: {thunder_state:.1f})"
            elif is_raining:
                return f"[weather] 打雷下雨 (雷电强度: {thunder_state:.1f})"
            else:
                return f"[weather] 雷声轰鸣 (雷电强度: {thunder_state:.1f})"
        else:
            return f"[weather] 天气变化: {weather} (下雨: {is_raining}, 雷电: {thunder_state:.1f})"
    def get_weather_description(self) -> str:
        """获取详细的天气描述"""
        weather = self.data.weather
        is_raining = self.data.isRaining
        thunder_state = self.data.thunderState

        if weather == "clear":
            return "晴朗"
        elif weather == "rain":
            return "下雨" if is_raining else "雨停"
        elif weather == "thunder":
            if thunder_state > 0.7:
                return "暴风雨"
            elif thunder_state > 0.3:
                return "雷雨"
            else:
                return "小雷雨" if is_raining else "雷声"
        else:
            return f"未知天气: {weather}"
