"""
时间戳工具函数 - 处理MCP server时间戳格式转换
"""
from typing import Union


def normalize_timestamp(timestamp: Union[int, float]) -> Union[int, float]:
    """
    标准化时间戳格式

    MCP server发送的是毫秒级时间戳，但Python的datetime需要秒级时间戳。
    此函数自动检测时间戳格式并转换为秒级。

    Args:
        timestamp: 输入时间戳（毫秒级或秒级）

    Returns:
        秒级时间戳

    Examples:
        >>> normalize_timestamp(1704067200000)  # 毫秒级
        1704067200.0
        >>> normalize_timestamp(1704067200)    # 秒级
        1704067200
    """
    if isinstance(timestamp, (int, float)) and timestamp > 1e10:
        # 如果是毫秒级时间戳（> 1e10），转换为秒级
        return timestamp / 1000.0
    else:
        # 秒级时间戳直接返回
        return timestamp


def is_millisecond_timestamp(timestamp: Union[int, float]) -> bool:
    """
    检查时间戳是否为毫秒级格式

    Args:
        timestamp: 时间戳

    Returns:
        如果是毫秒级返回True，否则返回False
    """
    return isinstance(timestamp, (int, float)) and timestamp > 1e10


def format_timestamp_for_display(timestamp: Union[int, float], format_str: str = "%H:%M:%S") -> str:
    """
    格式化时间戳为显示字符串

    Args:
        timestamp: 输入时间戳
        format_str: 时间格式字符串

    Returns:
        格式化后的时间字符串

    Examples:
        >>> format_timestamp_for_display(1704067200000)
        '08:00:00'
    """
    import time
    normalized_ts = normalize_timestamp(timestamp)
    return time.strftime(format_str, time.localtime(normalized_ts))


def get_current_timestamp_ms() -> int:
    """
    获取当前时间的毫秒级时间戳

    Returns:
        当前时间的毫秒级时间戳
    """
    import time
    return int(time.time() * 1000)


def get_current_timestamp_s() -> float:
    """
    获取当前时间的秒级时间戳

    Returns:
        当前时间的秒级时间戳
    """
    import time
    return time.time()


def convert_timestamp_for_datetime(timestamp: Union[int, float]) -> Union[int, float]:
    """
    将时间戳转换为datetime兼容的格式（秒级）

    Args:
        timestamp: 输入时间戳

    Returns:
        datetime.fromtimestamp()兼容的时间戳
    """
    return normalize_timestamp(timestamp)
