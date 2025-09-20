"""
API路由模块
包含所有FastAPI路由定义
"""

from .logs import logs_router, logs_ws_router
from .game_ws import game_ws_router
from .token_usage_ws import token_usage_ws_router
from .tasks_ws import tasks_ws_router
from .game_rest import game_rest_router
from .locations import locations_router
from .containers import containers_router
from .blocks import blocks_router
from .mcp import mcp_router

__all__ = [
    "logs_router",
    "logs_ws_router",
    "game_ws_router",
    "token_usage_ws_router",
    "tasks_ws_router",
    "game_rest_router",
    "locations_router",
    "containers_router",
    "blocks_router",
    "mcp_router"
]
