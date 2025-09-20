"""
统一WebSocket处理器基类
提供统一的WebSocket连接管理、心跳机制和消息处理
"""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Set
from fastapi import WebSocket, WebSocketDisconnect

from .config import api_config
from utils.logger import get_logger

logger = get_logger("WebSocketBase")


class BaseWebSocketHandler(ABC):
    """WebSocket处理器基类"""

    def __init__(self, handler_name: str = "BaseHandler"):
        self.handler_name = handler_name
        self.logger = get_logger(f"WS-{handler_name}")
        self.connected_clients: Dict[WebSocket, Dict[str, Any]] = {}
        self._heartbeat_tasks: Dict[WebSocket, asyncio.Task] = {}
        self._shutdown_event = asyncio.Event()

    async def handle_connection(self, websocket: WebSocket) -> None:
        """统一的WebSocket连接处理"""
        try:
            await websocket.accept()
            self.logger.info(f"客户端 {websocket} 已连接")

            # 初始化客户端配置
            client_config = self._create_client_config()
            self.connected_clients[websocket] = client_config

            # 发送欢迎消息
            await self._send_welcome_message(websocket)

            # 启动心跳监控
            self._start_heartbeat_monitor(websocket)

            # 处理连接
            await self._handle_connection_loop(websocket, client_config)

        except WebSocketDisconnect:
            self.logger.info(f"客户端 {websocket} 正常断开")
        except Exception as e:
            self.logger.error(f"WebSocket连接处理错误: {e}")
        finally:
            # 清理连接
            await self._cleanup_connection(websocket)

    def _create_client_config(self) -> Dict[str, Any]:
        """创建客户端配置"""
        return {
            "connected_at": time.time(),
            "last_heartbeat": time.time(),
            "last_activity": time.time(),
            "is_active": True,
            "handler_name": self.handler_name
        }

    async def _send_welcome_message(self, websocket: WebSocket) -> None:
        """发送欢迎消息"""
        welcome_data = {
            "type": "welcome",
            "message": f"已连接到 {self.handler_name} 服务",
            "timestamp": int(time.time() * 1000),
            "config": {
                "heartbeat_interval": api_config.websocket.heartbeat_interval,
                "timeout": api_config.websocket.heartbeat_timeout
            }
        }
        await websocket.send_json(welcome_data)

    def _start_heartbeat_monitor(self, websocket: WebSocket) -> None:
        """启动心跳监控任务"""
        task = asyncio.create_task(self._heartbeat_monitor_task(websocket))
        self._heartbeat_tasks[websocket] = task

    async def _heartbeat_monitor_task(self, websocket: WebSocket) -> None:
        """心跳监控任务"""
        while not self._shutdown_event.is_set():
            try:
                # 检查是否仍然连接
                if websocket not in self.connected_clients:
                    break

                client_config = self.connected_clients[websocket]
                current_time = time.time()

                # 检查心跳超时
                if current_time - client_config["last_heartbeat"] > api_config.websocket.heartbeat_timeout:
                    self.logger.warning(f"客户端 {websocket} 心跳超时，断开连接")
                    await self._force_disconnect(websocket)
                    break

                # 发送服务器心跳
                try:
                    await websocket.send_json({
                        "type": "ping",
                        "timestamp": int(current_time * 1000),
                        "message": f"服务器心跳 - {self.handler_name}"
                    })
                    self.logger.debug(f"发送服务器心跳: {websocket}")
                except Exception:
                    self.logger.warning(f"发送心跳失败: {websocket}")
                    break

                # 等待下一个心跳周期
                await asyncio.sleep(api_config.websocket.heartbeat_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"心跳监控任务错误: {e}")
                break

    async def _handle_connection_loop(self, websocket: WebSocket, client_config: Dict[str, Any]) -> None:
        """连接循环处理"""
        while not self._shutdown_event.is_set():
            try:
                # 设置超时时间
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=api_config.websocket.heartbeat_timeout
                )

                # 更新活动时间
                client_config["last_activity"] = time.time()

                # 处理消息
                await self._handle_message(websocket, message, client_config)

            except asyncio.TimeoutError:
                # 超时处理
                self.logger.debug(f"客户端 {websocket} 接收超时")
                break
            except WebSocketDisconnect:
                self.logger.info(f"客户端 {websocket} 断开连接")
                break
            except Exception as e:
                self.logger.error(f"消息处理循环错误: {e}")
                await self._handle_error(websocket, e)
                break

    async def _handle_message(self, websocket: WebSocket, message: str, client_config: Dict[str, Any]) -> None:
        """处理接收到的消息"""
        try:
            data = json.loads(message)
            message_type = data.get("type")

            # 更新心跳时间
            client_config["last_heartbeat"] = time.time()

            # 路由消息到具体处理方法
            if message_type == "ping":
                await self._handle_ping(websocket, data, client_config)
            elif message_type == "pong":
                await self._handle_pong(websocket, data, client_config)
            else:
                # 调用子类处理特定消息
                await self.handle_custom_message(websocket, message_type, data, client_config)

        except json.JSONDecodeError:
            await self._send_error(websocket, "无效的JSON格式", "INVALID_JSON")
        except Exception as e:
            await self._send_error(websocket, f"消息处理失败: {str(e)}", "MESSAGE_PROCESSING_ERROR")

    async def _handle_ping(self, websocket: WebSocket, data: dict, client_config: Dict[str, Any]) -> None:
        """处理客户端ping"""
        client_timestamp = data.get("timestamp", 0)

        # 更新最后心跳时间
        client_config["last_heartbeat"] = time.time()

        # 发送pong响应
        await websocket.send_json({
            "type": "pong",
            "timestamp": client_timestamp,
            "server_timestamp": int(time.time() * 1000)
        })

    async def _handle_pong(self, websocket: WebSocket, data: dict, client_config: Dict[str, Any]) -> None:
        """处理客户端pong响应"""
        # 更新最后心跳时间
        client_config["last_heartbeat"] = time.time()
        self.logger.debug(f"收到客户端pong响应: {websocket}")

    async def _send_error(self, websocket: WebSocket, message: str, error_code: str = "UNKNOWN_ERROR") -> None:
        """发送错误消息"""
        try:
            await websocket.send_json({
                "type": "error",
                "error_code": error_code,
                "message": message,
                "timestamp": int(time.time() * 1000)
            })
        except Exception:
            # 连接可能已断开，忽略错误
            pass

    async def _handle_error(self, websocket: WebSocket, error: Exception) -> None:
        """处理错误"""
        await self._send_error(websocket, f"连接处理错误: {str(error)}", "CONNECTION_ERROR")

    async def _force_disconnect(self, websocket: WebSocket) -> None:
        """强制断开连接"""
        try:
            await websocket.close()
        except Exception:
            pass

    async def _cleanup_connection(self, websocket: WebSocket) -> None:
        """清理连接"""
        # 从连接列表中移除
        if websocket in self.connected_clients:
            del self.connected_clients[websocket]

        # 取消心跳任务
        if websocket in self._heartbeat_tasks:
            task = self._heartbeat_tasks[websocket]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self._heartbeat_tasks[websocket]

        # 调用子类清理方法
        await self.cleanup_client(websocket)

        self.logger.info(f"已清理客户端连接: {websocket}")

    async def broadcast_to_clients(self, message: Dict[str, Any], exclude_websocket: Optional[WebSocket] = None) -> None:
        """广播消息给所有连接的客户端"""
        disconnected_clients = []

        for websocket in self.connected_clients:
            if websocket == exclude_websocket:
                continue

            try:
                await websocket.send_json(message)
            except Exception as e:
                self.logger.warning(f"广播消息失败: {websocket}, 错误: {e}")
                disconnected_clients.append(websocket)

        # 清理断开的连接
        for websocket in disconnected_clients:
            await self._cleanup_connection(websocket)

    async def send_to_client(self, websocket: WebSocket, message: Dict[str, Any]) -> bool:
        """发送消息给指定客户端"""
        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            self.logger.warning(f"发送消息失败: {websocket}, 错误: {e}")
            await self._cleanup_connection(websocket)
            return False

    async def cleanup_inactive_clients(self) -> None:
        """清理不活跃的客户端"""
        current_time = time.time()
        inactive_clients = []
        timeout = api_config.websocket.heartbeat_timeout

        for websocket, config in self.connected_clients.items():
            if current_time - config["last_heartbeat"] > timeout:
                inactive_clients.append(websocket)

        for websocket in inactive_clients:
            self.logger.info(f"清理不活跃客户端: {websocket}")
            await self._cleanup_connection(websocket)

    async def shutdown(self) -> None:
        """关闭处理器"""
        self._shutdown_event.set()

        # 取消所有心跳任务
        for task in self._heartbeat_tasks.values():
            if not task.done():
                task.cancel()

        # 等待任务完成
        await asyncio.gather(*self._heartbeat_tasks.values(), return_exceptions=True)

        # 清理所有连接
        for websocket in list(self.connected_clients.keys()):
            await self._cleanup_connection(websocket)

        self.logger.info(f"{self.handler_name} 处理器已关闭")

    # 子类需要实现的抽象方法
    @abstractmethod
    async def handle_custom_message(self, websocket: WebSocket, message_type: str, data: dict, client_config: Dict[str, Any]) -> None:
        """处理子类特定的消息类型"""
        pass

    @abstractmethod
    async def cleanup_client(self, websocket: WebSocket) -> None:
        """清理子类特定的客户端数据"""
        pass
