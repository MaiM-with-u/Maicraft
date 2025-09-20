"""
事件处理器包

包含各种Minecraft事件的处理器，负责处理特定的事件逻辑。
处理器可以中断当前任务、触发紧急响应等。
"""

from .hurt_response.hurt_response_handler import setup_hurt_response_handlers

__all__ = ["setup_hurt_response_handlers"]
