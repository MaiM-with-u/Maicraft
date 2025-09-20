"""
Token使用量WebSocket路由
提供实时Token使用量数据推送
"""

import asyncio
import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from openai_client.token_usage_manager import TokenUsageManager
from ..services.subscription_manager import subscription_manager, SubscriptionType
from utils.logger import get_logger

logger = get_logger("TokenUsageWSRouter")

# 创建路由器
token_usage_ws_router = APIRouter(prefix="/ws", tags=["token_usage_websocket"])


class TokenUsageWebSocketHandler:
    """Token使用量WebSocket处理器"""

    def __init__(self):
        self.subscription_type = SubscriptionType.TOKEN_USAGE
        # 使用全局token管理器实例，确保数据共享
        from openai_client.token_usage_manager import get_global_token_manager
        self.token_manager = get_global_token_manager()
        self.last_update_data: Dict[str, Any] = {}

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
            "update_interval": 0,  # Token使用量默认实时推送
            "last_heartbeat": time.time(),
            "subscribed": False,
            "model_filter": None,  # 可选的模型过滤器
            "awaiting_pong": False,  # 是否正在等待pong响应
            "last_ping_sent": 0,     # 最后发送ping的时间
            "last_client_ping": 0,   # 最后收到客户端ping的时间
        }

        try:
            while True:
                # 设置30秒超时
                try:
                    message = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=60.0  # 增加超时时间到60秒
                    )
                    await self._handle_message(websocket, message, client_config)

                except asyncio.TimeoutError:
                    # 检查心跳超时（最后心跳超过90秒视为超时）
                    if time.time() - client_config["last_heartbeat"] > 90:
                        logger.info(f"客户端 {websocket} 心跳超时，断开连接")
                        break
                    # 发送ping保持连接活跃
                    try:
                        current_time = time.time()
                        await websocket.send_json({
                            "type": "ping",
                            "timestamp": int(current_time * 1000),
                            "message": "服务器保持连接ping"
                        })
                        logger.debug(f"发送服务器ping保持连接: {websocket}")

                        # 设置等待pong响应的标志
                        client_config["awaiting_pong"] = True
                        client_config["last_ping_sent"] = current_time

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
            logger.info(f"清理客户端连接和订阅: {websocket}")
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
            elif message_type == "get_usage":
                await self._handle_get_usage(websocket, data, client_config)
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
        update_interval = data.get("update_interval", 0)  # Token使用量默认实时推送
        model_filter = data.get("model_filter")  # 可选的模型过滤器

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
            "model_filter": model_filter,
            "last_heartbeat": time.time()
        })

        # 发送确认消息
        await websocket.send_json({
            "type": "subscribed",
            "message": f"已订阅 {self.subscription_type.value} 数据",
            "subscription": {
                "type": self.subscription_type.value,
                "update_interval": update_interval,
                "model_filter": model_filter
            },
            "timestamp": int(time.time() * 1000)
        })

        # 立即发送一次当前数据
        await self._send_current_usage_data(websocket, model_filter)

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
        """处理客户端ping"""
        current_time = time.time()
        client_timestamp = data.get("timestamp", 0)

        # 更新最后心跳时间
        client_config["last_heartbeat"] = current_time

        # 检查客户端ping频率是否合理（防止滥发ping）
        last_ping_time = client_config.get("last_client_ping", 0)
        min_ping_interval = 1.0  # 最短ping间隔1秒

        if current_time - last_ping_time < min_ping_interval:
            logger.warning(f"客户端 {websocket} ping频率过高，忽略此次ping")
            return

        # 更新最后客户端ping时间
        client_config["last_client_ping"] = current_time

        # 发送pong响应
        await websocket.send_json({
            "type": "pong",
            "timestamp": client_timestamp,
            "server_timestamp": int(current_time * 1000)
        })

        logger.debug(f"回复客户端ping: {websocket}")

    async def _handle_pong(self, websocket: WebSocket, data: dict, client_config: Dict[str, Any]) -> None:
        """处理客户端对服务器ping的响应"""
        current_time = time.time()
        client_timestamp = data.get("timestamp", 0)

        # 更新最后心跳时间
        client_config["last_heartbeat"] = current_time

        # 验证pong响应是否有效
        if not client_config.get("awaiting_pong", False):
            # 如果服务器没有在等待pong，这可能是客户端主动发送的ping/pong
            # 对于token_usage_ws，我们允许这种情况，不做严格验证
            logger.debug(f"收到客户端主动pong: {websocket}")
        else:
            # 这是对服务器ping的响应，清除等待标志
            logger.debug(f"收到服务器ping的pong响应: {websocket}")

        # 清除等待pong响应的标志
        client_config["awaiting_pong"] = False

        logger.debug(f"收到有效的pong响应: {websocket}")

    async def _handle_get_usage(self, websocket: WebSocket, data: dict, client_config: Dict[str, Any]) -> None:
        """处理获取使用量请求"""
        model_name = data.get("model_name")
        model_filter = data.get("model_filter") or client_config.get("model_filter")

        await self._send_current_usage_data(websocket, model_filter, model_name)

    async def _send_current_usage_data(self, websocket: WebSocket, model_filter: Optional[str] = None, specific_model: Optional[str] = None) -> None:
        """发送当前使用量数据"""
        try:
            if specific_model:
                # 获取特定模型的数据
                usage_data = self.token_manager.get_usage_summary(specific_model)
                if usage_data["total_calls"] > 0:  # 只发送有数据的模型
                    message = {
                        "type": "token_usage_update",
                        "timestamp": int(time.time() * 1000),
                        "data": {
                            "model_name": specific_model,
                            "usage": usage_data
                        }
                    }
                    await websocket.send_json(message)
            else:
                # 获取所有模型的数据
                all_usage = self.token_manager.get_all_models_usage()
                filtered_usage = {}

                if model_filter:
                    # 应用模型过滤器
                    for model_name, usage in all_usage.items():
                        if model_filter in model_name:
                            filtered_usage[model_name] = usage
                else:
                    filtered_usage = all_usage

                # 只发送有数据的模型
                active_models = {k: v for k, v in filtered_usage.items() if v.get("total_calls", 0) > 0}

                if active_models:
                    message = {
                        "type": "token_usage_update",
                        "timestamp": int(time.time() * 1000),
                        "data": {
                            "models": active_models,
                            "summary": self.token_manager.get_total_cost_summary()
                        }
                    }
                    await websocket.send_json(message)

        except Exception as e:
            logger.error(f"发送使用量数据失败: {e}")

    def on_usage_update(self, model_name: str, usage_data: Dict[str, Any]) -> None:
        """Token使用量更新回调"""
        # 存储最新数据
        self.last_update_data[model_name] = usage_data

        # 检查是否有订阅的客户端
        if not subscription_manager.subscriptions[self.subscription_type]:
            logger.debug(f"没有订阅客户端，跳过推送: {model_name}")
            return

        # 异步推送给所有订阅的客户端
        try:
            # 尝试获取当前事件循环
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._broadcast_update(model_name, usage_data))
                logger.debug(f"在当前事件循环中创建推送任务: {model_name}")
            except RuntimeError:
                # 如果没有运行中的事件循环，调度到新的线程中运行
                import threading
                def run_in_thread():
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(self._broadcast_update(model_name, usage_data))
                        loop.close()
                    except Exception as e:
                        logger.error(f"线程中推送失败: {e}")
                
                thread = threading.Thread(target=run_in_thread, daemon=True)
                thread.start()
                logger.debug(f"在新线程中创建推送任务: {model_name}")
        except Exception as e:
            logger.error(f"创建推送任务失败: {e}")
            # 记录失败但不抛出异常，避免影响token记录

    async def _broadcast_update(self, model_name: str, usage_data: Dict[str, Any]) -> None:
        """广播使用量更新给所有订阅的客户端"""
        subscription_count = len(subscription_manager.subscriptions[self.subscription_type])
        logger.debug(f"开始广播Token使用量更新: {model_name}, 订阅客户端数: {subscription_count}")

        if not subscription_manager.subscriptions[self.subscription_type]:
            logger.debug(f"没有客户端订阅 {self.subscription_type.value}，跳过推送")
            return

        timestamp = int(time.time() * 1000)

        # 准备推送消息
        message = {
            "type": "token_usage_update",
            "timestamp": timestamp,
            "data": {
                "model_name": model_name,
                "usage": usage_data,
                "summary": self.token_manager.get_total_cost_summary()
            }
        }

        # 推送给所有活跃的WebSocket连接
        sent_count = 0

        for websocket in subscription_manager.subscriptions[self.subscription_type]:
            try:
                config = subscription_manager.client_configs.get(websocket)
                if config:
                    model_filter = config.get("model_filter")
                    # 检查是否匹配模型过滤器
                    if model_filter is None or model_filter in model_name:
                        logger.debug(f"推送给客户端: {model_name} -> {websocket}")
                        await websocket.send_json(message)
                        sent_count += 1
                    else:
                        logger.debug(f"客户端过滤器不匹配: {model_filter} not in {model_name}")
                else:
                    logger.warning(f"客户端缺少配置: {websocket}")
            except Exception as e:
                logger.warning(f"推送给客户端失败: {e}")
                # 注意：推送失败不一定意味着连接断开
                # 可能是客户端处理不过来或者临时阻塞
                # 让心跳机制来检测真正的连接断开

        # 注意：不再在这里清理断开的连接
        # 推送失败的客户端由心跳机制检测和清理
        # 这样可以避免误删正常但暂时阻塞的连接

        logger.debug(f"广播完成: 发送给 {sent_count} 个客户端")


# 创建处理器实例
token_usage_handler = TokenUsageWebSocketHandler()

# 注意：全局回调设置在server.py的_setup_routes中完成
# token_manager已经在构造函数中使用get_global_token_manager()获取


@token_usage_ws_router.websocket("/token-usage")
async def websocket_token_usage(websocket: WebSocket):
    """Token使用量WebSocket端点"""
    await token_usage_handler.handle_connection(websocket)
