"""
订阅管理器服务
处理WebSocket订阅机制和数据推送
"""

import asyncio
import json
import time
from typing import Dict, Any, Set, Optional, Callable
from enum import Enum

from fastapi import WebSocket
from utils.logger import get_logger


class SubscriptionType(Enum):
    """订阅类型枚举"""
    PLAYER = "player"
    WORLD = "world"
    MARKER = "marker"
    TOKEN_USAGE = "token_usage"


class SubscriptionManager:
    """订阅管理器"""

    def __init__(self):
        self.logger = get_logger("SubscriptionManager")
        self.subscriptions: Dict[SubscriptionType, Set[WebSocket]] = {
            SubscriptionType.PLAYER: set(),
            SubscriptionType.WORLD: set(),
            SubscriptionType.MARKER: set(),
            SubscriptionType.TOKEN_USAGE: set()
        }
        self.client_configs: Dict[WebSocket, Dict[str, Any]] = {}
        self._shutdown_event = asyncio.Event()
        self._push_tasks: Dict[SubscriptionType, asyncio.Task] = {}

    async def subscribe(self, websocket: WebSocket, sub_type: SubscriptionType, update_interval: int = 1000) -> None:
        """订阅数据推送"""
        # 添加到订阅集合
        self.subscriptions[sub_type].add(websocket)

        # 保存客户端配置
        self.client_configs[websocket] = {
            "subscription_type": sub_type,
            "update_interval": update_interval,
            "subscribed_at": time.time()
        }

        self.logger.info(f"客户端 {websocket} 订阅了 {sub_type.value} 数据，更新间隔: {update_interval}ms")

        # 启动推送任务（如果还没有启动）
        if sub_type not in self._push_tasks or self._push_tasks[sub_type].done():
            self._push_tasks[sub_type] = asyncio.create_task(
                self._push_data_task(sub_type)
            )

    async def unsubscribe(self, websocket: WebSocket) -> None:
        """取消订阅"""
        # 从所有订阅集合中移除
        for sub_type in SubscriptionType:
            self.subscriptions[sub_type].discard(websocket)

        # 清理客户端配置
        if websocket in self.client_configs:
            config = self.client_configs[websocket]
            self.logger.info(f"客户端 {websocket} 取消订阅了 {config.get('subscription_type', 'unknown')}")
            del self.client_configs[websocket]

    async def handle_message(self, websocket: WebSocket, message: str) -> None:
        """处理WebSocket消息"""
        try:
            data = json.loads(message)
            message_type = data.get("type")

            if message_type == "subscribe":
                await self._handle_subscribe(websocket, data)
            elif message_type == "unsubscribe":
                await self._handle_unsubscribe(websocket)
            elif message_type == "ping":
                await self._handle_ping(websocket, data)
            else:
                await self._send_error(websocket, f"未知消息类型: {message_type}")

        except json.JSONDecodeError:
            await self._send_error(websocket, "无效的JSON格式")
        except Exception as e:
            await self._send_error(websocket, f"消息处理失败: {str(e)}")

    async def _handle_subscribe(self, websocket: WebSocket, data: dict) -> None:
        """处理订阅请求"""
        update_interval = data.get("update_interval", 1000)

        # 验证更新间隔
        if update_interval < 0:
            await self._send_error(websocket, "更新间隔不能为负数", "INVALID_INTERVAL")
            return

        # 确定订阅类型（基于WebSocket路径）
        # 这个需要在路由层传递订阅类型信息
        # 这里暂时使用默认类型，实际使用时需要修改
        sub_type = SubscriptionType.PLAYER  # 默认值，需要在路由层设置

        # 取消之前的订阅
        await self.unsubscribe(websocket)

        # 建立新订阅
        await self.subscribe(websocket, sub_type, update_interval)

        # 发送确认消息
        await websocket.send_json({
            "type": "subscribed",
            "message": f"已订阅 {sub_type.value} 数据",
            "subscription": {
                "type": sub_type.value,
                "update_interval": update_interval
            },
            "timestamp": int(time.time() * 1000)
        })

    async def _handle_unsubscribe(self, websocket: WebSocket) -> None:
        """处理取消订阅"""
        await self.unsubscribe(websocket)

        await websocket.send_json({
            "type": "unsubscribed",
            "message": "已取消订阅",
            "timestamp": int(time.time() * 1000)
        })

    async def _handle_ping(self, websocket: WebSocket, data: dict) -> None:
        """处理心跳请求"""
        client_timestamp = data.get("timestamp", 0)

        # 更新最后心跳时间
        if websocket in self.client_configs:
            self.client_configs[websocket]["last_heartbeat"] = time.time()

        # 发送pong响应
        await websocket.send_json({
            "type": "pong",
            "timestamp": client_timestamp,
            "server_timestamp": int(time.time() * 1000)
        })

    async def _send_error(self, websocket: WebSocket, message: str, error_code: str = "UNKNOWN_ERROR") -> None:
        """发送错误消息"""
        try:
            await websocket.send_json({
                "type": "error",
                "errorCode": error_code,
                "message": message,
                "timestamp": int(time.time() * 1000)
            })
        except Exception:
            # 连接可能已断开，忽略错误
            pass

    async def _push_data_task(self, sub_type: SubscriptionType) -> None:
        """数据推送任务"""
        while not self._shutdown_event.is_set():
            try:
                # 获取活跃的WebSocket连接
                active_websockets = []

                for websocket in self.subscriptions[sub_type]:
                    config = self.client_configs.get(websocket)
                    if config:
                        # 不再检查心跳超时，只要WebSocket连接存在就认为是活跃的
                        # WebSocket的心跳机制会处理连接断开
                        active_websockets.append((websocket, config))

                # 推送数据给活跃连接
                if active_websockets:
                    # 获取数据（这里需要外部注入数据获取函数）
                    data = await self._get_data_for_type(sub_type)
                    if data:
                        timestamp = int(time.time() * 1000)

                        for websocket, config in active_websockets:
                            try:
                                update_interval = config["update_interval"]
                                if update_interval == 0:
                                    # 仅在数据变化时推送
                                    await self._send_data_update(websocket, sub_type, data, timestamp)
                                else:
                                    # 定期推送
                                    await self._send_data_update(websocket, sub_type, data, timestamp)
                            except Exception as e:
                                self.logger.warning(f"推送数据失败: {e}")
                                # 从订阅中移除失败的连接
                                self.subscriptions[sub_type].discard(websocket)
                                if websocket in self.client_configs:
                                    del self.client_configs[websocket]

                # 计算下次推送的时间
                min_interval = float('inf')
                for websocket, config in active_websockets:
                    interval = config["update_interval"]
                    if interval > 0:
                        min_interval = min(min_interval, interval)

                if min_interval == float('inf'):
                    # 没有定期推送的需求，等待较长时间
                    await asyncio.sleep(5.0)
                else:
                    # 转换为秒并等待
                    await asyncio.sleep(min_interval / 1000.0)

            except Exception as e:
                self.logger.error(f"数据推送任务错误: {e}")
                await asyncio.sleep(1.0)

    async def _get_data_for_type(self, sub_type: SubscriptionType) -> Optional[Dict[str, Any]]:
        """获取指定类型的数据"""
        try:
            if sub_type == SubscriptionType.PLAYER:
                from .game_state_service import game_state_service
                return game_state_service.get_player_data()
            elif sub_type == SubscriptionType.WORLD:
                from .game_state_service import game_state_service
                return game_state_service.get_world_data()
            elif sub_type == SubscriptionType.MARKER:
                from .game_state_service import game_state_service
                return game_state_service.get_marker_data()
            elif sub_type == SubscriptionType.TOKEN_USAGE:
                # Token使用量通过事件驱动，不需要定期获取
                return None
            else:
                return None
        except Exception as e:
            self.logger.error(f"获取 {sub_type.value} 数据失败: {e}")
            return None

    async def _send_data_update(self, websocket: WebSocket, sub_type: SubscriptionType,
                               data: Dict[str, Any], timestamp: int) -> None:
        """发送数据更新"""
        message = {
            "type": f"{sub_type.value}_update",
            "timestamp": timestamp,
            "data": data
        }
        await websocket.send_json(message)

    def set_data_provider(self, sub_type: SubscriptionType, provider: Callable) -> None:
        """设置数据提供者"""
        # 这里可以设置数据获取函数
        # 为了简化实现，我们将在游戏状态路由中直接调用
        pass

    async def cleanup_inactive_connections(self) -> None:
        """清理不活跃的连接"""
        current_time = time.time()
        inactive_threshold = 60  # 60秒没有心跳视为不活跃

        for sub_type in SubscriptionType:
            inactive_websockets = []
            for websocket in self.subscriptions[sub_type]:
                config = self.client_configs.get(websocket)
                if config and current_time - config["last_heartbeat"] > inactive_threshold:
                    inactive_websockets.append(websocket)

            for websocket in inactive_websockets:
                self.logger.info(f"清理不活跃连接: {websocket}")
                await self.unsubscribe(websocket)

    async def shutdown(self) -> None:
        """关闭订阅管理器"""
        self._shutdown_event.set()

        # 取消所有推送任务
        for task in self._push_tasks.values():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # 清理所有连接
        for sub_type in SubscriptionType:
            self.subscriptions[sub_type].clear()

        self.client_configs.clear()


# 全局订阅管理器实例
subscription_manager = SubscriptionManager()
