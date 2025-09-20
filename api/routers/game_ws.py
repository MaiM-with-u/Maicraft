"""
游戏状态WebSocket路由
提供实时游戏状态数据推送
"""

import asyncio
import time
from typing import Dict, Any
from fastapi import APIRouter, WebSocket

from ..services.game_state_service import game_state_service
from ..services.subscription_manager import subscription_manager, SubscriptionType
from ..websocket_base import BaseWebSocketHandler
from ..config import api_config
from utils.logger import get_logger

logger = get_logger("GameWSRouter")

# 创建路由器
game_ws_router = APIRouter(prefix="/ws", tags=["game_websocket"])


class GameWebSocketHandler(BaseWebSocketHandler):
    """游戏WebSocket处理器"""

    def __init__(self, subscription_type: SubscriptionType):
        super().__init__(f"Game-{subscription_type.value}")
        self.subscription_type = subscription_type
        self.data_provider = self._get_data_provider()

    def _get_data_provider(self):
        """获取数据提供者函数"""
        if self.subscription_type == SubscriptionType.PLAYER:
            return game_state_service.get_player_data
        elif self.subscription_type == SubscriptionType.WORLD:
            return game_state_service.get_world_data
        elif self.subscription_type == SubscriptionType.MARKER:
            return game_state_service.get_marker_data
        else:
            return lambda: {}

    async def handle_custom_message(self, websocket: WebSocket, message_type: str, data: dict, client_config: Dict[str, Any]) -> None:
        """处理游戏相关的自定义消息"""
        if message_type == "subscribe":
            await self._handle_subscribe(websocket, data, client_config)
        elif message_type == "unsubscribe":
            await self._handle_unsubscribe(websocket, client_config)
        else:
            await self._send_error(websocket, f"未知消息类型: {message_type}", "UNKNOWN_MESSAGE_TYPE")

    async def _handle_subscribe(self, websocket: WebSocket, data: dict, client_config: Dict[str, Any]) -> None:
        """处理订阅请求"""
        update_interval = data.get("update_interval", api_config.subscription.default_update_interval)

        # 验证更新间隔
        min_interval = api_config.subscription.min_update_interval
        max_interval = api_config.subscription.max_update_interval

        if not isinstance(update_interval, int) or update_interval < min_interval or update_interval > max_interval:
            await self._send_error(
                websocket,
                f"更新间隔必须是{min_interval}-{max_interval}ms之间的整数",
                "INVALID_INTERVAL"
            )
            return

        # 取消之前的订阅
        if client_config.get("subscribed"):
            await subscription_manager.unsubscribe(websocket)

        # 订阅新数据
        await subscription_manager.subscribe(websocket, self.subscription_type, update_interval)

        # 更新客户端配置
        client_config.update({
            "update_interval": update_interval,
            "subscribed": True,
            "last_heartbeat": time.time()
        })

        # 发送确认消息
        await websocket.send_json({
            "type": "subscribed",
            "message": f"已订阅 {self.subscription_type.value} 数据",
            "subscription": {
                "type": self.subscription_type.value,
                "update_interval": update_interval
            },
            "timestamp": int(time.time() * 1000)
        })

        # 如果是定期推送，立即发送一次数据
        if update_interval > 0:
            await self._send_data_update(websocket)

    async def _handle_unsubscribe(self, websocket: WebSocket, client_config: Dict[str, Any]) -> None:
        """处理取消订阅"""
        await subscription_manager.unsubscribe(websocket)

        # 更新客户端配置
        client_config["subscribed"] = False

        await websocket.send_json({
            "type": "unsubscribed",
            "message": "已取消订阅",
            "timestamp": int(time.time() * 1000)
        })

    async def _send_data_update(self, websocket: WebSocket) -> None:
        """发送数据更新"""
        try:
            data = self.data_provider()
            timestamp = int(time.time() * 1000)

            message = {
                "type": f"{self.subscription_type.value}_update",
                "timestamp": timestamp,
                "data": data
            }

            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"发送数据更新失败: {e}")

    async def cleanup_client(self, websocket: WebSocket) -> None:
        """清理客户端特定的数据"""
        # 取消订阅
        client_config = self.connected_clients.get(websocket)
        if client_config and client_config.get("subscribed"):
            await subscription_manager.unsubscribe(websocket)


# 创建处理器实例
player_handler = GameWebSocketHandler(SubscriptionType.PLAYER)
world_handler = GameWebSocketHandler(SubscriptionType.WORLD)
marker_handler = GameWebSocketHandler(SubscriptionType.MARKER)


@game_ws_router.websocket("/game/player")
async def websocket_game_player(websocket: WebSocket):
    """玩家数据WebSocket端点"""
    await player_handler.handle_connection(websocket)


@game_ws_router.websocket("/game/world")
async def websocket_game_world(websocket: WebSocket):
    """世界数据WebSocket端点"""
    await world_handler.handle_connection(websocket)


@game_ws_router.websocket("/game/marker")
async def websocket_game_marker(websocket: WebSocket):
    """标记点数据WebSocket端点"""
    await marker_handler.handle_connection(websocket)
