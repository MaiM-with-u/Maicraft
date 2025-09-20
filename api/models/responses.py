"""
API响应数据模型
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from enum import Enum


class ErrorCode(str, Enum):
    """错误码枚举"""
    # 系统级错误
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"

    # 业务级错误
    INVALID_PARAMETER = "INVALID_PARAMETER"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    OPERATION_FAILED = "OPERATION_FAILED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

    # WebSocket相关
    CONNECTION_ERROR = "CONNECTION_ERROR"
    SUBSCRIPTION_ERROR = "SUBSCRIPTION_ERROR"

    # 游戏相关
    GAME_STATE_ERROR = "GAME_STATE_ERROR"
    ENVIRONMENT_ERROR = "ENVIRONMENT_ERROR"


class ApiResponse(BaseModel):
    """通用API响应模型（已弃用，请使用UnifiedApiResponse）

    @deprecated: 此模型已弃用，请使用UnifiedApiResponse以获得更好的响应格式
    """
    is_success: bool
    message: str
    data: Optional[Any] = None
    timestamp: Optional[int] = None
    error_code: Optional[str] = None


class UnifiedApiResponse(BaseModel):
    """统一的API响应模型"""
    code: str  # SUCCESS, ERROR, WARNING
    success: bool
    message: str
    data: Optional[Any] = None
    timestamp: Optional[int] = None
    error_code: Optional[str] = None


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
