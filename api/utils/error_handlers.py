"""
API错误处理工具
提供统一的错误响应生成和异常处理
"""

import time
import traceback
from typing import Any, Optional
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from ..models.responses import ApiResponse, ErrorCode
from utils.logger import get_logger

logger = get_logger("APIErrorHandler")


class APIError(Exception):
    """API业务异常基类"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        data: Optional[Any] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.data = data
        super().__init__(message)


class ValidationError(APIError):
    """验证错误"""

    def __init__(self, message: str, data: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=status.HTTP_400_BAD_REQUEST,
            data=data
        )


class NotFoundError(APIError):
    """资源未找到错误"""

    def __init__(self, message: str = "Resource not found", data: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND,
            data=data
        )


class OperationFailedError(APIError):
    """操作失败错误"""

    def __init__(self, message: str, data: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.OPERATION_FAILED,
            status_code=status.HTTP_400_BAD_REQUEST,
            data=data
        )


def create_success_response(
    data: Any = None,
    message: str = "Success",
    include_timestamp: bool = True
) -> ApiResponse:
    """创建成功响应"""
    timestamp = int(time.time() * 1000) if include_timestamp else None
    return ApiResponse(
        is_success=True,
        message=message,
        data=data,
        timestamp=timestamp
    )


def create_error_response(
    message: str,
    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
    data: Optional[Any] = None,
    include_timestamp: bool = True
) -> ApiResponse:
    """创建错误响应"""
    timestamp = int(time.time() * 1000) if include_timestamp else None
    return ApiResponse(
        is_success=False,
        message=message,
        error_code=error_code,
        data=data,
        timestamp=timestamp
    )


def handle_api_error(error: Exception) -> JSONResponse:
    """处理API异常，返回标准的JSON响应"""

    # 如果是API业务异常
    if isinstance(error, APIError):
        response = create_error_response(
            message=error.message,
            error_code=error.error_code,
            data=error.data
        )
        return JSONResponse(
            status_code=error.status_code,
            content=response.model_dump()
        )

    # 如果是HTTP异常
    elif isinstance(error, HTTPException):
        response = create_error_response(
            message=error.detail,
            error_code=ErrorCode.INTERNAL_ERROR
        )
        return JSONResponse(
            status_code=error.status_code,
            content=response.model_dump()
        )

    # 其他未知异常
    else:
        # 记录详细错误信息
        logger.error(f"Unhandled exception: {str(error)}")
        logger.error(f"Traceback: {traceback.format_exc()}")

        response = create_error_response(
            message="Internal server error",
            error_code=ErrorCode.INTERNAL_ERROR
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response.model_dump()
        )


def handle_route_error(func_name: str, error: Exception) -> ApiResponse:
    """处理路由级别的错误，返回ApiResponse对象"""

    # 记录错误
    logger.warning(f"Error in {func_name}: {str(error)}")

    # 如果是API业务异常
    if isinstance(error, APIError):
        return create_error_response(
            message=error.message,
            error_code=error.error_code,
            data=error.data
        )

    # 如果是值错误（通常是参数验证错误）
    elif isinstance(error, ValueError):
        return create_error_response(
            message=str(error),
            error_code=ErrorCode.VALIDATION_ERROR
        )

    # 如果是查找错误
    elif isinstance(error, KeyError) or isinstance(error, IndexError):
        return create_error_response(
            message="Resource not found",
            error_code=ErrorCode.RESOURCE_NOT_FOUND
        )

    # 其他异常
    else:
        logger.error(f"Unexpected error in {func_name}: {str(error)}")
        logger.error(f"Traceback: {traceback.format_exc()}")

        return create_error_response(
            message="Operation failed",
            error_code=ErrorCode.OPERATION_FAILED
        )


# 便捷的装饰器
def api_error_handler(func_name: str = None):
    """API错误处理装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                function_name = func_name or func.__name__
                return handle_route_error(function_name, e)
        return wrapper
    return decorator
