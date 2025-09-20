"""
游戏状态WebSocket路由
提供实时游戏状态数据推送
"""

import asyncio
import time
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services.game_state_service import game_state_service
from ..services.subscription_manager import subscription_manager, SubscriptionType
from utils.logger import get_logger

logger = get_logger("GameWSRouter")

# 创建路由器
game_ws_router = APIRouter(tags=["game_websocket"])


class GameWebSocketHandler:
    """游戏WebSocket处理器"""

    def __init__(self, subscription_type: SubscriptionType):
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

    async def handle_connection(self, websocket: WebSocket) -> None:
        """处理WebSocket连接"""
        await websocket.accept()

        # 发送欢迎消息
        await websocket.send_json({
            "type": "welcome",
            "message": f"已连接到 {self.subscription_type.value} 数据服务器",
            "timestamp": int(time.time() * 1000)
        })

        # 初始化客户端配置
        client_config = {
            "subscription_type": self.subscription_type,
            "update_interval": 1000,  # 默认1秒
            "last_heartbeat": time.time(),
            "subscribed": False
        }

        try:
            while True:
                # 设置60秒超时
                try:
                    message = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=60.0
                    )
                    await self._handle_message(websocket, message, client_config)

                except asyncio.TimeoutError:
                    # 检查心跳超时（最后心跳超过90秒视为超时）
                    if time.time() - client_config["last_heartbeat"] > 90:
                        logger.info(f"客户端 {websocket} 心跳超时，断开连接")
                        break
                    # 发送ping保持连接活跃
                    try:
                        await websocket.send_json({
                            "type": "ping",
                            "timestamp": int(time.time() * 1000),
                            "message": "服务器保持连接ping"
                        })
                        logger.debug(f"发送服务器ping保持连接: {websocket}")
                    except Exception:
                        logger.warning(f"发送服务器ping失败: {websocket}")
                        break
                    continue

        except WebSocketDisconnect:
            logger.info(f"客户端 {websocket} 断开连接")
        except Exception as e:
            logger.error(f"WebSocket连接错误: {e}")
        finally:
            # 清理订阅
            if client_config.get("subscribed"):
                await subscription_manager.unsubscribe(websocket)

    async def _handle_message(self, websocket: WebSocket, message: str, client_config: Dict[str, Any]) -> None:
        """处理WebSocket消息"""
        try:
            import json
            data = json.loads(message)
            message_type = data.get("type")

            if message_type == "subscribe":
                await self._handle_subscribe(websocket, data, client_config)
            elif message_type == "unsubscribe":
                await self._handle_unsubscribe(websocket, client_config)
            elif message_type == "ping":
                await self._handle_ping(websocket, data, client_config)
            elif message_type == "pong":
                await self._handle_pong(websocket, data, client_config)
            else:
                await websocket.send_json({
                    "type": "error",
                    "errorCode": "UNKNOWN_MESSAGE_TYPE",
                    "message": f"未知消息类型: {message_type}",
                    "timestamp": int(time.time() * 1000)
                })

        except json.JSONDecodeError:
            await websocket.send_json({
                "type": "error",
                "errorCode": "INVALID_JSON",
                "message": "无效的JSON格式",
                "timestamp": int(time.time() * 1000)
            })
        except Exception as e:
            await websocket.send_json({
                "type": "error",
                "errorCode": "MESSAGE_PROCESSING_ERROR",
                "message": f"消息处理失败: {str(e)}",
                "timestamp": int(time.time() * 1000)
            })

    async def _handle_subscribe(self, websocket: WebSocket, data: dict, client_config: Dict[str, Any]) -> None:
        """处理订阅请求"""
        update_interval = data.get("update_interval", 1000)

        # 验证更新间隔
        if not isinstance(update_interval, int) or update_interval < 0:
            await websocket.send_json({
                "type": "error",
                "errorCode": "INVALID_INTERVAL",
                "message": "更新间隔必须是非负整数",
                "timestamp": int(time.time() * 1000)
            })
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

    async def _handle_ping(self, websocket: WebSocket, data: dict, client_config: Dict[str, Any]) -> None:
        """处理心跳请求"""
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
        """处理客户端对服务器ping的响应"""
        # 更新最后心跳时间
        client_config["last_heartbeat"] = time.time()
        logger.debug(f"收到客户端pong响应: {websocket}")

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


# 创建处理器实例
player_handler = GameWebSocketHandler(SubscriptionType.PLAYER)
world_handler = GameWebSocketHandler(SubscriptionType.WORLD)
marker_handler = GameWebSocketHandler(SubscriptionType.MARKER)


@game_ws_router.websocket("/ws/game/player")
async def websocket_game_player(websocket: WebSocket):
    """玩家数据WebSocket端点"""
    await player_handler.handle_connection(websocket)


@game_ws_router.websocket("/ws/game/world")
async def websocket_game_world(websocket: WebSocket):
    """世界数据WebSocket端点"""
    await world_handler.handle_connection(websocket)


@game_ws_router.websocket("/ws/game/marker")
async def websocket_game_marker(websocket: WebSocket):
    """标记点数据WebSocket端点"""
    await marker_handler.handle_connection(websocket)
