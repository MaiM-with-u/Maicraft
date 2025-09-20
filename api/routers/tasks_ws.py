"""
任务管理WebSocket路由
提供实时任务状态数据推送和管理
"""

import asyncio
import time
from contextlib import suppress
from typing import Dict, Any
from fastapi import APIRouter, WebSocket

from ..websocket_base import BaseWebSocketHandler
from agent.to_do_list import mai_to_do_list
from utils.logger import get_logger

logger = get_logger("TasksWSRouter")

# 创建路由器
tasks_ws_router = APIRouter(prefix="/ws", tags=["tasks_websocket"])


class TasksWebSocketHandler(BaseWebSocketHandler):
    """任务WebSocket处理器"""

    def __init__(self):
        super().__init__("Tasks")

    async def handle_custom_message(self, websocket: WebSocket, message_type: str, data: dict, client_config: Dict[str, Any]) -> None:
        """处理任务相关的自定义消息"""
        if message_type == "subscribe":
            await self._handle_subscribe(websocket, data, client_config)
        elif message_type == "unsubscribe":
            await self._handle_unsubscribe(websocket, client_config)
        elif message_type == "get_tasks":
            await self._handle_get_tasks(websocket, data, client_config)
        elif message_type == "add_task":
            await self._handle_add_task(websocket, data, client_config)
        elif message_type == "update_task":
            await self._handle_update_task(websocket, data, client_config)
        elif message_type == "delete_task":
            await self._handle_delete_task(websocket, data, client_config)
        elif message_type == "mark_done":
            await self._handle_mark_done(websocket, data, client_config)
        else:
            await self._send_error(websocket, f"未知消息类型: {message_type}", "UNKNOWN_MESSAGE_TYPE")

    async def _handle_subscribe(self, websocket: WebSocket, data: dict, client_config: Dict[str, Any]) -> None:
        """处理订阅请求"""
        update_interval = data.get("update_interval", 5000)  # 默认5秒更新一次

        # 验证更新间隔
        min_interval = 1000  # 最短1秒
        max_interval = 30000  # 最长30秒

        if not isinstance(update_interval, int) or update_interval < min_interval or update_interval > max_interval:
            await self._send_error(
                websocket,
                f"更新间隔必须是{min_interval}-{max_interval}ms之间的整数",
                "INVALID_INTERVAL"
            )
            return

        # 取消之前的订阅
        if client_config.get("subscribed"):
            await self._handle_unsubscribe(websocket, client_config)

        # 订阅任务更新
        client_config.update({
            "update_interval": update_interval,
            "subscribed": True,
            "last_heartbeat": time.time()
        })

        # 任务更新现在是事件驱动的，不再需要定期推送
        # 只有当任务发生变化时才会推送更新

        # 发送确认消息
        await websocket.send_json({
            "type": "subscribed",
            "message": "已订阅任务数据更新",
            "subscription": {
                "type": "tasks",
                "update_interval": update_interval
            },
            "timestamp": int(time.time() * 1000)
        })

        # 立即发送一次任务数据
        await self._send_task_update(websocket)

    async def _handle_unsubscribe(self, websocket: WebSocket, client_config: Dict[str, Any]) -> None:
        """处理取消订阅"""
        # 更新客户端配置
        client_config["subscribed"] = False

        await websocket.send_json({
            "type": "unsubscribed",
            "message": "已取消订阅任务数据",
            "timestamp": int(time.time() * 1000)
        })

    async def _handle_get_tasks(self, websocket: WebSocket, data: dict, client_config: Dict[str, Any]) -> None:
        """处理获取任务列表请求"""
        # 获取任务数据
        tasks_data = self._get_tasks_data()

        await websocket.send_json({
            "type": "tasks_list",
            "message": "任务列表获取成功",
            "data": tasks_data,
            "timestamp": int(time.time() * 1000)
        })

    async def _handle_add_task(self, websocket: WebSocket, data: dict, client_config: Dict[str, Any]) -> None:
        """处理添加任务请求"""
        try:
            details = data.get("details", "").strip()
            done_criteria = data.get("done_criteria", "").strip()

            if not details:
                await self._send_error(websocket, "任务详情不能为空", "VALIDATION_ERROR")
                return

            if not done_criteria:
                await self._send_error(websocket, "完成条件不能为空", "VALIDATION_ERROR")
                return

            # 添加新任务
            new_task = mai_to_do_list.add_task(details, done_criteria)

            # 广播任务更新给所有订阅者（排除当前客户端）
            await self._broadcast_task_update(exclude_websocket=websocket)

            # 发送确认消息给当前客户端
            await websocket.send_json({
                "type": "task_added",
                "message": "任务添加成功",
                "data": {
                    "task_id": new_task.id,
                    "details": new_task.details,
                    "done_criteria": new_task.done_criteria,
                    "progress": new_task.progress,
                    "done": new_task.done
                },
                "timestamp": int(time.time() * 1000)
            })

        except Exception as e:
            logger.error(f"添加任务失败: {e}")
            await self._send_error(websocket, f"添加任务失败: {str(e)}", "OPERATION_FAILED")

    async def _handle_update_task(self, websocket: WebSocket, data: dict, client_config: Dict[str, Any]) -> None:
        """处理更新任务请求"""
        try:
            task_id = data.get("task_id", "").strip()
            progress = data.get("progress", "").strip()

            if not task_id:
                await self._send_error(websocket, "任务ID不能为空", "VALIDATION_ERROR")
                return

            # 更新任务进度
            mai_to_do_list.update_task_progress(task_id, progress)

            # 广播任务更新给所有订阅者（排除当前客户端）
            await self._broadcast_task_update(exclude_websocket=websocket)

            # 发送确认消息
            await websocket.send_json({
                "type": "task_updated",
                "message": "任务更新成功",
                "data": {
                    "task_id": task_id,
                    "progress": progress
                },
                "timestamp": int(time.time() * 1000)
            })

        except Exception as e:
            logger.error(f"更新任务失败: {e}")
            await self._send_error(websocket, f"更新任务失败: {str(e)}", "OPERATION_FAILED")

    async def _handle_delete_task(self, websocket: WebSocket, data: dict, client_config: Dict[str, Any]) -> None:
        """处理删除任务请求"""
        try:
            task_id = data.get("task_id", "").strip()

            if not task_id:
                await self._send_error(websocket, "任务ID不能为空", "VALIDATION_ERROR")
                return

            # 删除任务
            mai_to_do_list.del_task_by_id(task_id)

            # 广播任务更新给所有订阅者（排除当前客户端）
            await self._broadcast_task_update(exclude_websocket=websocket)

            # 发送确认消息
            await websocket.send_json({
                "type": "task_deleted",
                "message": "任务删除成功",
                "data": {
                    "task_id": task_id
                },
                "timestamp": int(time.time() * 1000)
            })

        except Exception as e:
            logger.error(f"删除任务失败: {e}")
            await self._send_error(websocket, f"删除任务失败: {str(e)}", "OPERATION_FAILED")

    async def _handle_mark_done(self, websocket: WebSocket, data: dict, client_config: Dict[str, Any]) -> None:
        """处理标记任务完成请求"""
        try:
            task_id = data.get("task_id", "").strip()

            if not task_id:
                await self._send_error(websocket, "任务ID不能为空", "VALIDATION_ERROR")
                return

            # 标记任务完成
            mai_to_do_list.mark_task_done(task_id)

            # 广播任务更新给所有订阅者（排除当前客户端）
            await self._broadcast_task_update(exclude_websocket=websocket)

            # 发送确认消息
            await websocket.send_json({
                "type": "task_marked_done",
                "message": "任务标记完成成功",
                "data": {
                    "task_id": task_id
                },
                "timestamp": int(time.time() * 1000)
            })

        except Exception as e:
            logger.error(f"标记任务完成失败: {e}")
            await self._send_error(websocket, f"标记任务完成失败: {str(e)}", "OPERATION_FAILED")

    def _get_tasks_data(self) -> Dict[str, Any]:
        """获取任务数据"""
        tasks = [
            {
                "id": item.id,
                "details": item.details,
                "done_criteria": item.done_criteria,
                "progress": item.progress,
                "done": item.done
            }
            for item in mai_to_do_list.items
        ]

        return {
            "tasks": tasks,
            "total": len(tasks),
            "completed": len([t for t in tasks if t["done"]]),
            "pending": len([t for t in tasks if not t["done"]]),
            "goal": mai_to_do_list.mai_goal.goal if hasattr(mai_to_do_list, 'mai_goal') else "",
            "is_done": mai_to_do_list.check_if_all_done()
        }

    async def _send_task_update(self, websocket: WebSocket) -> None:
        """发送任务更新"""
        try:
            tasks_data = self._get_tasks_data()

            await websocket.send_json({
                "type": "tasks_update",
                "timestamp": int(time.time() * 1000),
                "data": tasks_data
            })
        except Exception as e:
            logger.error(f"发送任务更新失败: {e}")

    async def _broadcast_task_update(self, exclude_websocket: WebSocket = None) -> None:
        """广播任务更新给所有订阅者（排除指定客户端）"""
        for websocket in self.connected_clients:
            # 排除发起操作的客户端，避免重复推送
            if websocket == exclude_websocket:
                continue

            client_config = self.connected_clients[websocket]
            if client_config.get("subscribed"):
                await self._send_task_update(websocket)


    async def cleanup_client(self, websocket: WebSocket) -> None:
        """清理客户端特定的数据"""
        # 任务更新现在是事件驱动的，不再需要定期任务清理


# 创建处理器实例
tasks_handler = TasksWebSocketHandler()


@tasks_ws_router.websocket("/tasks")
async def websocket_tasks(websocket: WebSocket):
    """任务数据WebSocket端点"""
    await tasks_handler.handle_connection(websocket)
