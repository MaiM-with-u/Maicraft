"""
API响应数据模型
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ApiResponse(BaseModel):
    """通用API响应模型"""
    isSuccess: bool
    message: str
    data: Optional[Any] = None
    timestamp: Optional[int] = None


class LogConfigResponse(BaseModel):
    """日志配置响应模型"""
    level: str


class LogEntry(BaseModel):
    """日志条目模型"""
    timestamp: int
    level: str
    module: str
    message: str
    file: Optional[str] = None
    line: Optional[int] = None


class LogStats(BaseModel):
    """日志统计信息模型"""
    total_logs: int
    level_counts: Dict[str, int]
    module_counts: Dict[str, int]
    time_range: Dict[str, Optional[str]]
    max_capacity: int
    utilization_percent: float


class LogRecentResponse(BaseModel):
    """最近日志响应模型"""
    logs: List[LogEntry]
    total: int
    has_more: bool
