"""
健康事件处理器包

专门处理Minecraft中的健康相关事件，特别是当生命值过低时中断当前任务进行紧急处理。
"""

from .health_event_handler import setup_health_handlers

__all__ = ["setup_health_handlers"]
