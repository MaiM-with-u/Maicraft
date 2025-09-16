"""
API路由模块
包含所有FastAPI路由定义
"""

from .logs import logs_router, websocket_router
from .game_ws import game_ws_router
from .game_rest import game_rest_router
from .locations import locations_router
from .containers import containers_router
from .blocks import blocks_router
from .mcp import mcp_router

__all__ = [
    "logs_router",
    "websocket_router",
    "game_ws_router",
    "game_rest_router",
    "locations_router",
    "containers_router",
    "blocks_router",
    "mcp_router"
]
