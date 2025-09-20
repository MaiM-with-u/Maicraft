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
from ..config import api_config


class WebSocketManager:
    """WebSocket管理器"""

    def __init__(self):
        self.logger = get_logger_manager()
        self.connected_clients: Dict[WebSocket, Dict[str, Any]] = {}
        self._log_listener_task: asyncio.Task = None
        self._cleanup_task: asyncio.Task = None
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
            "connected_at": time.time(),
            "awaiting_pong": False,
            "last_ping_sent": 0,
            "last_client_ping": 0
        }
        self.connected_clients[websocket] = client_info

        # 启动清理任务（如果还没有启动）
        self._start_cleanup_task()

        # 发送欢迎消息
        await websocket.send_json({
            "type": "welcome",
            "message": "已连接到MaicraftAgent日志服务器",
            "timestamp": int(time.time() * 1000),
            "config": {
                "heartbeat_interval": api_config.websocket.heartbeat_interval,
                "timeout": api_config.websocket.heartbeat_timeout
            }
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
            elif message_type == "pong":
                await self._handle_pong(websocket, data)
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
        current_time = time.time()
        client_timestamp = data.get("timestamp", 0)

        # 更新最后心跳时间
        if websocket in self.connected_clients:
            client_info = self.connected_clients[websocket]
            client_info["last_heartbeat"] = current_time

            # 检查客户端ping频率是否合理（防止滥发ping）
            last_ping_time = client_info.get("last_client_ping", 0)
            min_ping_interval = 1.0  # 最短ping间隔1秒

            if current_time - last_ping_time < min_ping_interval:
                self.logger.warning(f"客户端 {websocket} ping频率过高，忽略此次ping")
                return

            # 更新最后客户端ping时间
            client_info["last_client_ping"] = current_time

        # 发送pong响应
        await websocket.send_json({
            "type": "pong",
            "timestamp": client_timestamp,
            "server_timestamp": int(current_time * 1000)
        })

        self.logger.debug(f"回复客户端ping: {websocket}")

    async def _handle_pong(self, websocket: WebSocket, data: dict) -> None:
        """处理客户端对服务器ping的响应"""
        current_time = time.time()
        client_timestamp = data.get("timestamp", 0)

        # 更新最后心跳时间
        if websocket in self.connected_clients:
            client_info = self.connected_clients[websocket]
            client_info["last_heartbeat"] = current_time

            # 验证pong响应是否有效
            if not client_info.get("awaiting_pong", False):
                # 如果服务器没有在等待pong，这可能是一个意外的pong
                self.logger.warning(f"收到意外的pong响应，服务端未发送过ping给客户端 {websocket}")
                return

            # 验证时间戳是否合理（pong的时间戳应该接近服务器发送ping的时间戳）
            last_ping_sent = client_info.get("last_ping_sent", 0)
            if abs(client_timestamp / 1000 - last_ping_sent) > 10:  # 允许10秒的时钟偏差
                self.logger.warning(f"收到无效的pong时间戳，客户端 {websocket}")
                return

            # 清除等待pong响应的标志
            client_info["awaiting_pong"] = False

            self.logger.debug(f"收到有效的pong响应: {websocket}")

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

    def _start_cleanup_task(self) -> None:
        """启动清理任务"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_monitor_task())
            self.logger.debug("WebSocket管理器清理任务已启动")

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

    async def _cleanup_monitor_task(self) -> None:
        """定期清理不活跃客户端的任务"""
        cleanup_interval = api_config.websocket.cleanup_interval

        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(cleanup_interval)
                if not self._shutdown_event.is_set():
                    await self._cleanup_inactive_clients()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"清理监控任务错误: {e}")
                break

    async def _log_listener(self) -> None:
        """日志监听器，不断检查新日志并推送给客户端"""
        last_log_count = 0
        heartbeat_interval = api_config.websocket.heartbeat_interval
        next_heartbeat_time = time.time() + heartbeat_interval

        while not self._shutdown_event.is_set():
            try:
                current_time = time.time()

                # 检查是否需要发送心跳
                if current_time >= next_heartbeat_time:
                    await self._send_heartbeat_ping()
                    next_heartbeat_time = current_time + heartbeat_interval

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

    async def _cleanup_inactive_clients(self) -> None:
        """清理不活跃的客户端"""
        current_time = time.time()
        inactive_clients = []
        timeout = api_config.websocket.heartbeat_timeout

        for websocket, client_info in self.connected_clients.items():
            # 检查心跳超时
            if current_time - client_info["last_heartbeat"] > timeout:
                inactive_clients.append(websocket)

        for websocket in inactive_clients:
            self.logger.info(f"清理不活跃客户端: {websocket}")
            if websocket in self.connected_clients:
                del self.connected_clients[websocket]

    async def _send_heartbeat_ping(self) -> None:
        """发送心跳ping给所有客户端"""
        current_time = time.time()
        disconnected_clients = []

        for websocket, client_info in self.connected_clients.items():
            try:
                # 检查是否正在等待pong响应
                if client_info["awaiting_pong"] and (current_time - client_info["last_ping_sent"] > api_config.websocket.heartbeat_timeout):
                    self.logger.warning(f"客户端 {websocket} pong响应超时，断开连接")
                    disconnected_clients.append(websocket)
                    continue

                # 发送ping
                await websocket.send_json({
                    "type": "ping",
                    "timestamp": int(current_time * 1000),
                    "message": "服务器心跳 - 日志服务"
                })

                # 标记正在等待pong响应
                client_info["awaiting_pong"] = True
                client_info["last_ping_sent"] = current_time

            except Exception as e:
                self.logger.warning(f"发送心跳失败: {websocket}, 错误: {e}")
                disconnected_clients.append(websocket)

        # 清理断开的客户端
        for websocket in disconnected_clients:
            if websocket in self.connected_clients:
                del self.connected_clients[websocket]

    async def shutdown(self) -> None:
        """关闭WebSocket管理器"""
        await self.stop_log_listener()

        # 停止清理任务
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

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
