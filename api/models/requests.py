"""
API请求数据模型
"""

from typing import Optional, List
from pydantic import BaseModel


class LogSubscription(BaseModel):
    """日志订阅请求模型"""
    type: str = "subscribe"
    levels: Optional[List[str]] = None
    modules: Optional[List[str]] = None


class HeartbeatMessage(BaseModel):
    """心跳消息模型"""
    type: str = "ping"
    timestamp: int


class LogLevelUpdate(BaseModel):
    """日志级别更新请求模型"""
    level: str
