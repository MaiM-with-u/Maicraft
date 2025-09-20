"""
统一错误处理和响应规范化
提供统一的API响应格式和错误处理机制
"""

import time
import traceback
from typing import Any, Optional, Dict, Union
from enum import Enum
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from .models.responses import ErrorCode
from utils.logger import get_logger

logger = get_logger("APIErrorHandler")


class APIResponseCode(str, Enum):
    """API响应状态码"""
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    WARNING = "WARNING"


class UnifiedAPIResponse:
    """统一的API响应格式"""

    @staticmethod
    def success(
        data: Any = None,
        message: str = "操作成功",
        include_timestamp: bool = True
    ) -> Dict[str, Any]:
        """成功响应"""
        response = {
            "code": APIResponseCode.SUCCESS,
            "success": True,
            "message": message,
            "data": data
        }
        if include_timestamp:
            response["timestamp"] = int(time.time() * 1000)
        return response

    @staticmethod
    def error(
        error_code: Union[str, ErrorCode] = ErrorCode.INTERNAL_ERROR,
        message: str = "操作失败",
        data: Optional[Any] = None,
        status_code: int = 500,
        include_timestamp: bool = True
    ) -> tuple[Dict[str, Any], int]:
        """错误响应"""
        response = {
            "code": APIResponseCode.ERROR,
            "success": False,
            "message": message,
            "error_code": error_code if isinstance(error_code, str) else error_code.value,
            "data": data
        }
        if include_timestamp:
            response["timestamp"] = int(time.time() * 1000)
        return response, status_code

    @staticmethod
    def warning(
        message: str,
        data: Optional[Any] = None,
        include_timestamp: bool = True
    ) -> Dict[str, Any]:
        """警告响应"""
        response = {
            "code": APIResponseCode.WARNING,
            "success": True,
            "message": message,
            "data": data
        }
        if include_timestamp:
            response["timestamp"] = int(time.time() * 1000)
        return response


def handle_route_error(
    func_name: str,
    error: Exception,
    include_traceback: bool = False
) -> tuple[Dict[str, Any], int]:
    """处理路由级别的错误，返回统一格式的响应"""

    # 记录错误
    logger.warning(f"Error in {func_name}: {str(error)}")

    # 如果是API业务异常
    if isinstance(error, APIError):
        return UnifiedAPIResponse.error(
            error_code=error.error_code,
            message=error.message,
            data=error.data,
            status_code=error.status_code
        )

    # 如果是HTTP异常
    elif isinstance(error, HTTPException):
        return UnifiedAPIResponse.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message=error.detail,
            status_code=error.status_code
        )

    # 如果是值错误（通常是参数验证错误）
    elif isinstance(error, ValueError):
        return UnifiedAPIResponse.error(
            error_code=ErrorCode.VALIDATION_ERROR,
            message=str(error),
            status_code=400
        )

    # 如果是查找错误
    elif isinstance(error, (KeyError, IndexError, AttributeError)):
        return UnifiedAPIResponse.error(
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            message="资源未找到或数据格式错误",
            status_code=404
        )

    # 其他异常
    else:
        error_msg = str(error)
        if include_traceback:
            error_msg += f"\n{traceback.format_exc()}"

        logger.error(f"Unexpected error in {func_name}: {error_msg}")

        return UnifiedAPIResponse.error(
            error_code=ErrorCode.OPERATION_FAILED,
            message="操作执行失败",
            status_code=500
        )


class APIError(Exception):
    """API业务异常基类"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        status_code: int = 500,
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
            status_code=400,
            data=data
        )


class NotFoundError(APIError):
    """资源未找到错误"""

    def __init__(self, message: str = "Resource not found", data: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            status_code=404,
            data=data
        )


class OperationFailedError(APIError):
    """操作失败错误"""

    def __init__(self, message: str, data: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.OPERATION_FAILED,
            status_code=400,
            data=data
        )


def create_api_exception_handler(app):
    """为FastAPI应用添加统一的异常处理器"""

    @app.exception_handler(APIError)
    async def handle_api_error(request: Request, exc: APIError):
        """处理API业务异常"""
        response, status_code = UnifiedAPIResponse.error(
            error_code=exc.error_code,
            message=exc.message,
            data=exc.data,
            status_code=exc.status_code
        )
        return JSONResponse(status_code=status_code, content=response)

    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException):
        """处理HTTP异常"""
        response, status_code = UnifiedAPIResponse.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message=exc.detail,
            status_code=exc.status_code
        )
        return JSONResponse(status_code=status_code, content=response)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        """处理未预期的异常"""
        logger.error(f"Unhandled exception: {str(exc)}")
        logger.error(f"Traceback: {traceback.format_exc()}")

        response, status_code = UnifiedAPIResponse.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="服务器内部错误",
            status_code=500
        )
        return JSONResponse(status_code=status_code, content=response)


# 便捷的响应创建函数
def create_success_response(data: Any = None, message: str = "操作成功") -> Dict[str, Any]:
    """创建成功响应"""
    return UnifiedAPIResponse.success(data=data, message=message)


def create_error_response(
    error_code: Union[str, ErrorCode] = ErrorCode.INTERNAL_ERROR,
    message: str = "操作失败",
    data: Optional[Any] = None
) -> tuple[Dict[str, Any], int]:
    """创建错误响应"""
    return UnifiedAPIResponse.error(
        error_code=error_code,
        message=message,
        data=data
    )
