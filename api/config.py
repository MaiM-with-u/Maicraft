"""
API模块配置管理
集中管理所有API相关的配置项
"""

from dataclasses import dataclass
from typing import Optional, List
from config import global_config


@dataclass
class WebSocketConfig:
    """WebSocket相关配置"""
    heartbeat_interval: int = 60  # 心跳间隔(秒)
    heartbeat_timeout: int = 90   # 心跳超时时间(秒)
    max_connections: int = 100    # 最大连接数
    cleanup_interval: int = 30    # 清理不活跃连接间隔(秒)


@dataclass
class CORSConfig:
    """CORS相关配置"""
    enabled: bool = True
    allow_origins: List[str] = None
    allow_credentials: bool = True
    allow_methods: List[str] = None
    allow_headers: List[str] = None

    def __post_init__(self):
        if self.allow_origins is None:
            self.allow_origins = ["*"]
        if self.allow_methods is None:
            self.allow_methods = ["*"]
        if self.allow_headers is None:
            self.allow_headers = ["*"]


@dataclass
class ServerConfig:
    """服务器相关配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    access_log: bool = False


@dataclass
class SubscriptionConfig:
    """订阅相关配置"""
    default_update_interval: int = 1000  # 默认更新间隔(ms)
    max_update_interval: int = 30000     # 最大更新间隔(ms)
    min_update_interval: int = 100       # 最小更新间隔(ms)


@dataclass
class APIConfig:
    """API模块总配置"""
    server: ServerConfig = None
    websocket: WebSocketConfig = None
    cors: CORSConfig = None
    subscription: SubscriptionConfig = None

    def __post_init__(self):
        if self.server is None:
            self.server = ServerConfig()
        if self.websocket is None:
            self.websocket = WebSocketConfig()
        if self.cors is None:
            self.cors = CORSConfig()
        if self.subscription is None:
            self.subscription = SubscriptionConfig()


# 全局API配置实例
def create_api_config() -> APIConfig:
    """从全局配置创建API配置实例"""
    # 从全局配置中读取相关设置
    api_config = global_config.api

    return APIConfig(
        server=ServerConfig(
            host=getattr(api_config, 'host', '0.0.0.0'),
            port=getattr(api_config, 'port', 8000),
            log_level=getattr(api_config, 'log_level', 'info'),
            access_log=False  # 默认关闭访问日志
        ),
        websocket=WebSocketConfig(
            heartbeat_interval=60,
            heartbeat_timeout=90,
            max_connections=100,
            cleanup_interval=30
        ),
        cors=CORSConfig(
            enabled=getattr(api_config, 'enable_cors', True),
            allow_origins=["*"],  # 生产环境请限制域名
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"]
        ),
        subscription=SubscriptionConfig(
            default_update_interval=1000,
            max_update_interval=30000,
            min_update_interval=100
        )
    )


# 全局API配置实例
api_config = create_api_config()
