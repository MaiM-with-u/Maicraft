"""
MaicraftAgent API服务器
提供WebSocket和REST API接口
"""

import asyncio
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import global_config
from utils.logger import get_logger

# 获取当前模块的日志器
logger = get_logger("APIServer")
from .routers.logs import lifespan
from .routers import (
    logs_router,
    logs_ws_router,
    game_ws_router,
    token_usage_ws_router,
    game_rest_router,
    locations_router,
    containers_router,
    blocks_router,
    mcp_router
)


class MaicraftAPIServer:
    """MaicraftAgent API服务器"""

    def __init__(self):
        self.app = FastAPI(
            title="MaicraftAgent API",
            version="1.0.0",
            description="MaicraftAgent WebSocket和REST API服务器",
            lifespan=lifespan
        )

        # 设置CORS（如果配置中启用）
        if global_config.api.enable_cors:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],  # 生产环境请限制域名
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        # 注册路由
        self._setup_routes()

    def _setup_routes(self):
        """设置路由"""
        # 设置Token使用量WebSocket回调
        from .routers.token_usage_ws import token_usage_handler
        from openai_client.token_usage_manager import set_global_token_manager_callback
        set_global_token_manager_callback(token_usage_handler.on_usage_update)

        # 包含路由器
        self.app.include_router(logs_router)
        self.app.include_router(logs_ws_router)
        self.app.include_router(game_ws_router)
        self.app.include_router(token_usage_ws_router)
        self.app.include_router(game_rest_router)
        self.app.include_router(locations_router)
        self.app.include_router(containers_router)
        self.app.include_router(blocks_router)
        self.app.include_router(mcp_router)

        # 健康检查端点
        @self.app.get("/health")
        async def health_check():
            """健康检查"""
            return {
                "status": "healthy",
                "service": "MaicraftAgent API",
                "version": "1.0.0"
            }


# 全局API服务器实例
_api_server = None


def get_api_server() -> MaicraftAPIServer:
    """获取全局API服务器实例"""
    global _api_server
    if _api_server is None:
        _api_server = MaicraftAPIServer()
    return _api_server


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    server = get_api_server()
    return server.app


async def start_api_server(host: Optional[str] = None, port: Optional[int] = None):
    """启动API服务器"""
    # 使用配置中的设置或参数中的设置
    api_config = global_config.api
    server_host = host or api_config.host
    server_port = port or api_config.port
    log_level = api_config.log_level

    # 检查MCP客户端连接状态（由main.py负责连接）
    try:
        from ...mcp_server.client import global_mcp_client
    except ImportError:
        # 如果相对导入失败，尝试绝对导入
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from mcp_server.client import global_mcp_client

    # 检查MCP是否已连接（由main.py负责）
    if global_mcp_client.connected:
        logger.info("MCP客户端已连接（由main.py管理）")
    else:
        logger.warning("MCP客户端未连接，API服务器可能无法正常工作。建议通过main.py启动系统。")

        # 作为备选方案，尝试连接MCP（仅在独立启动API服务器时）
        logger.info("尝试独立连接MCP客户端...")
        connected = await global_mcp_client.connect()
        if connected:
            logger.info("MCP客户端连接成功")
        else:
            logger.error("MCP客户端连接失败")

    app = create_app()

    # 配置uvicorn服务器
    config = uvicorn.Config(
        app,
        host=server_host,
        port=server_port,
        log_level=log_level,  # 使用配置中的日志级别
        access_log=False      # 关闭访问日志
    )

    server = uvicorn.Server(config)

    try:
        await server.serve()
    except KeyboardInterrupt:
        # 优雅退出
        pass

