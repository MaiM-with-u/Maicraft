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
from .routers.logs import lifespan
from .routers import (
    logs_router,
    websocket_router,
    game_ws_router,
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
        # 包含路由器
        self.app.include_router(logs_router)
        self.app.include_router(websocket_router)
        self.app.include_router(game_ws_router)
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

    # 连接MCP客户端
    try:
        from ...mcp_server.client import global_mcp_client
    except ImportError:
        # 如果相对导入失败，尝试绝对导入
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from mcp_server.client import global_mcp_client

    print("[API] 正在连接MCP客户端...")
    connected = await global_mcp_client.connect()
    if connected:
        print("[API] MCP客户端连接成功")
    else:
        print("[API] MCP客户端连接失败")

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


# 向后兼容的别名
get_websocket_server = get_api_server
create_websocket_app = create_app
start_websocket_server = start_api_server
