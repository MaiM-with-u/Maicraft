"""
日志相关路由
包含WebSocket和REST API路由
"""

import asyncio
from typing import Optional
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager

from ..models.requests import LogLevelUpdate
from ..models.responses import ApiResponse
from ..services.log_service import LogService
from ..services.websocket_manager import WebSocketManager

# 创建服务实例
log_service = LogService()
websocket_manager = WebSocketManager()

# 创建路由器
logs_router = APIRouter(prefix="/api/logs", tags=["logs"])

# 创建lifespan管理器
@asynccontextmanager
async def lifespan(app):
    """应用生命周期管理器"""
    # 启动时
    await websocket_manager.start_log_listener()

    yield

    # 关闭时
    await websocket_manager.shutdown()


@logs_router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket日志推送接口"""
    await websocket_manager.connect(websocket)

    try:
        while True:
            # 设置60秒超时
            try:
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0
                )
                await websocket_manager.handle_message(websocket, message)
            except asyncio.TimeoutError:
                # 检查心跳超时（最后心跳超过90秒视为超时）
                last_heartbeat = websocket_manager.connected_clients.get(websocket, {}).get("last_heartbeat", 0)
                if time.time() - last_heartbeat > 90:
                    # 心跳超时，断开连接
                    break
                # 发送ping保持连接活跃
                try:
                    await websocket.send_json({
                        "type": "ping",
                        "timestamp": int(time.time() * 1000),
                        "message": "服务器保持连接ping"
                    })
                except Exception:
                    # 发送ping失败，断开连接
                    break
                continue
            except WebSocketDisconnect:
                break
            except Exception as e:
                # 其他错误，检查心跳超时
                last_heartbeat = websocket_manager.connected_clients.get(websocket, {}).get("last_heartbeat", 0)
                if time.time() - last_heartbeat > 90:
                    # 心跳超时，断开连接
                    break

    except Exception as e:
        pass
    finally:
        # 清理客户端连接
        await websocket_manager.disconnect(websocket)


@logs_router.get("/config", response_model=ApiResponse)
async def get_logs_config():
    """获取当前日志配置"""
    try:
        config = log_service.get_config()
        return ApiResponse(
            isSuccess=True,
            message="success",
            data=config
        )
    except Exception as e:
        return ApiResponse(
            isSuccess=False,
            message=f"获取日志配置失败: {str(e)}",
            data=None
        )


@logs_router.get("/level", response_model=ApiResponse)
async def get_logs_level():
    """获取日志级别信息"""
    try:
        config = log_service.get_config()
        data = {
            "current_level": config["level"],
            "available_levels": ["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"]
        }
        return ApiResponse(
            isSuccess=True,
            message="success",
            data=data
        )
    except Exception as e:
        return ApiResponse(
            isSuccess=False,
            message=f"获取日志级别失败: {str(e)}",
            data=None
        )


@logs_router.post("/level", response_model=ApiResponse)
async def update_logs_level(request: LogLevelUpdate):
    """更新日志级别"""
    try:
        result = log_service.update_level(request.level)

        # 通知所有连接的客户端日志级别已更改
        await websocket_manager.broadcast_level_change(request.level.upper())

        return ApiResponse(
            isSuccess=True,
            message="success",
            data=result
        )
    except ValueError as e:
        return ApiResponse(
            isSuccess=False,
            message=str(e),
            data=None
        )
    except Exception as e:
        return ApiResponse(
            isSuccess=False,
            message=f"更新日志级别失败: {str(e)}",
            data=None
        )


@logs_router.get("/recent", response_model=ApiResponse)
async def get_recent_logs(
    limit: int = 100,
    level: Optional[str] = None,
    module: Optional[str] = None,
    message_contains: Optional[str] = None,
    since_minutes: Optional[int] = None
):
    """获取最近的日志记录"""
    try:
        result = log_service.get_recent_logs(
            limit=limit,
            level=level,
            module=module,
            message_contains=message_contains,
            since_minutes=since_minutes
        )

        return ApiResponse(
            isSuccess=True,
            message="success",
            data=result
        )
    except Exception as e:
        return ApiResponse(
            isSuccess=False,
            message=f"获取日志记录失败: {str(e)}",
            data=None
        )


@logs_router.get("/stats", response_model=ApiResponse)
async def get_logs_stats():
    """获取日志统计信息"""
    try:
        stats = log_service.get_stats()
        return ApiResponse(
            isSuccess=True,
            message="success",
            data=stats
        )
    except Exception as e:
        return ApiResponse(
            isSuccess=False,
            message=f"获取日志统计失败: {str(e)}",
            data=None
        )


@logs_router.post("/clear", response_model=ApiResponse)
async def clear_logs_cache():
    """清空日志缓存"""
    try:
        result = log_service.clear_logs()
        return ApiResponse(
            isSuccess=True,
            message="success",
            data=result
        )
    except Exception as e:
        return ApiResponse(
            isSuccess=False,
            message=f"清空日志缓存失败: {str(e)}",
            data=None
        )
