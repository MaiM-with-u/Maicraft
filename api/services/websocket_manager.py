"""
WebSocket管理器服务
处理WebSocket连接和消息分发
"""

import asyncio
import json
import time
from typing import Dict, Any, Set
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect
from utils.logger import get_logger_manager


class WebSocketManager:
    """WebSocket管理器"""

    def __init__(self):
        self.logger = get_logger_manager()
        self.connected_clients: Dict[WebSocket, Dict[str, Any]] = {}
        self._log_listener_task: asyncio.Task = None
        self._shutdown_event = asyncio.Event()

    async def connect(self, websocket: WebSocket) -> None:
        """处理新的WebSocket连接"""
        await websocket.accept()
        client_info = {
            "subscription": {
                "levels": None,  # None表示订阅所有级别
                "modules": None,  # None表示订阅所有模块
            },
            "last_heartbeat": time.time(),
            "connected_at": time.time()
        }
        self.connected_clients[websocket] = client_info

        # 发送欢迎消息
        await websocket.send_json({
            "type": "welcome",
            "message": "已连接到MaicraftAgent日志服务器",
            "timestamp": int(time.time() * 1000)
        })

    async def disconnect(self, websocket: WebSocket) -> None:
        """处理WebSocket断开连接"""
        if websocket in self.connected_clients:
            del self.connected_clients[websocket]

    async def handle_message(self, websocket: WebSocket, message: str) -> None:
        """处理WebSocket消息"""
        try:
            data = json.loads(message)
            message_type = data.get("type")

            if message_type == "subscribe":
                await self._handle_subscription(websocket, data)
            elif message_type == "ping":
                await self._handle_ping(websocket, data)
            elif message_type == "unsubscribe":
                await self._handle_unsubscribe(websocket)
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"未知消息类型: {message_type}",
                    "timestamp": int(time.time() * 1000)
                })

        except json.JSONDecodeError:
            await websocket.send_json({
                "type": "error",
                "message": "无效的JSON格式",
                "timestamp": int(time.time() * 1000)
            })
        except Exception as e:
            await websocket.send_json({
                "type": "error",
                "message": f"消息处理失败: {str(e)}",
                "timestamp": int(time.time() * 1000)
            })

    async def _handle_subscription(self, websocket: WebSocket, data: dict) -> None:
        """处理订阅请求"""
        levels = data.get("levels")
        modules = data.get("modules")

        # 更新客户端订阅信息
        if websocket in self.connected_clients:
            self.connected_clients[websocket]["subscription"] = {
                "levels": levels,
                "modules": modules
            }

        # 发送确认消息
        await websocket.send_json({
            "type": "subscribed",
            "message": "日志订阅已设置",
            "subscription": {
                "levels": levels,
                "modules": modules
            },
            "timestamp": int(time.time() * 1000)
        })

    async def _handle_ping(self, websocket: WebSocket, data: dict) -> None:
        """处理心跳请求"""
        client_timestamp = data.get("timestamp", 0)

        # 更新最后心跳时间
        if websocket in self.connected_clients:
            self.connected_clients[websocket]["last_heartbeat"] = time.time()

        # 发送pong响应
        await websocket.send_json({
            "type": "pong",
            "timestamp": client_timestamp,
            "server_timestamp": int(time.time() * 1000)
        })

    async def _handle_unsubscribe(self, websocket: WebSocket) -> None:
        """处理取消订阅"""
        if websocket in self.connected_clients:
            self.connected_clients[websocket]["subscription"] = {
                "levels": None,
                "modules": None
            }

        await websocket.send_json({
            "type": "unsubscribed",
            "message": "已取消日志订阅",
            "timestamp": int(time.time() * 1000)
        })

    def _should_send_to_client(self, log_entry: dict, client_subscription: dict) -> bool:
        """判断是否应该将日志发送给客户端"""
        # 检查级别过滤
        if client_subscription["levels"] is not None:
            if log_entry["level"].upper() not in [level.upper() for level in client_subscription["levels"]]:
                return False

        # 检查模块过滤
        if client_subscription["modules"] is not None:
            if not any(module.lower() in log_entry["module"].lower() for module in client_subscription["modules"]):
                return False

        return True

    async def broadcast_level_change(self, new_level: str) -> None:
        """广播日志级别更改"""
        message = {
            "type": "level_changed",
            "new_level": new_level,
            "timestamp": int(time.time() * 1000)
        }

        disconnected_clients = []
        for websocket, client_info in self.connected_clients.items():
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected_clients.append(websocket)

        # 清理断开的客户端
        for websocket in disconnected_clients:
            if websocket in self.connected_clients:
                del self.connected_clients[websocket]

    async def start_log_listener(self) -> None:
        """启动日志监听器"""
        if self._log_listener_task is None or self._log_listener_task.done():
            self._log_listener_task = asyncio.create_task(self._log_listener())

    async def stop_log_listener(self) -> None:
        """停止日志监听器"""
        if self._log_listener_task and not self._log_listener_task.done():
            self._shutdown_event.set()
            self._log_listener_task.cancel()
            try:
                await self._log_listener_task
            except asyncio.CancelledError:
                pass

    async def _log_listener(self) -> None:
        """日志监听器，不断检查新日志并推送给客户端"""
        last_log_count = 0

        while not self._shutdown_event.is_set():
            try:
                # 获取最近的日志
                recent_logs = self.logger._recent_logs

                # 检查是否有新日志
                if len(recent_logs) > last_log_count:
                    # 获取新增的日志
                    new_logs = recent_logs[last_log_count:]

                    # 向所有客户端推送新日志
                    disconnected_clients = []

                    for websocket, client_info in self.connected_clients.items():
                        try:
                            for log_entry in new_logs:
                                # 检查是否符合客户端的订阅条件
                                if self._should_send_to_client(log_entry, client_info["subscription"]):
                                    # 转换时间戳格式
                                    timestamp = int(datetime.fromisoformat(log_entry["timestamp"].replace('Z', '+00:00')).timestamp() * 1000)

                                    message = {
                                        "type": "log",
                                        "timestamp": timestamp,
                                        "level": log_entry["level"],
                                        "module": log_entry["module"],
                                        "message": log_entry["message"]
                                    }

                                    await websocket.send_json(message)

                        except Exception as e:
                            # 客户端可能已断开
                            disconnected_clients.append(websocket)

                    # 清理断开的客户端
                    for websocket in disconnected_clients:
                        if websocket in self.connected_clients:
                            del self.connected_clients[websocket]

                    last_log_count = len(recent_logs)

                # 每100ms检查一次新日志
                await asyncio.sleep(0.1)

            except Exception as e:
                # 记录错误但不中断监听
                print(f"日志监听器错误: {e}")
                await asyncio.sleep(1.0)

    async def shutdown(self) -> None:
        """关闭WebSocket管理器"""
        await self.stop_log_listener()

        # 关闭所有WebSocket连接
        close_tasks = []
        for websocket in self.connected_clients:
            close_tasks.append(websocket.close())

        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)

        self.connected_clients.clear()

    def get_connection_count(self) -> int:
        """获取当前连接数"""
        return len(self.connected_clients)
