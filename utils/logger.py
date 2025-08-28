from __future__ import annotations

from loguru import logger as _logger
import sys


def get_logger(name: str):
    """返回带有模块名绑定的loguru logger。"""
    return _logger.bind(module=name)


def setup_logging(level: str | None = None) -> None:
    """根据配置设置全局日志级别。

    Args:
        level: 日志级别字符串，如 "DEBUG"、"INFO"、"WARNING"、"ERROR"。
    """
    try:
        # 规范化级别
        level_str = (level or "INFO").upper()
        valid_levels = {"TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"}
        if level_str not in valid_levels:
            level_str = "INFO"

        # 重置默认处理器，添加新的级别设置（启用彩色控制台输出）
        _logger.remove()
        # 控制台输出（彩色 + 简洁格式）
        _logger.add(
            sys.stderr,
            level=level_str,
            colorize=True,
            enqueue=False,
            backtrace=False,
            diagnose=False,
            format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <1}</level> | <cyan>{extra[module]}</cyan> - <level>{message}</level>",
        )
    except Exception:
        # 出现异常时保持默认配置
        pass

