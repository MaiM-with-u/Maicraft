from __future__ import annotations

from typing import Any, Dict, List, Optional
import json
import os
import asyncio
import time
from enum import Enum
from dataclasses import dataclass
from fastmcp import Client as FastMCPClient
from fastmcp.client.client import CallToolResult
from mcp.types import Tool, TextContent
from utils.logger import get_logger


class ConnectionState(Enum):
    """MCP连接状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class ConnectionErrorType(Enum):
    """连接错误类型枚举"""
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_ERROR = "authentication_error"
    DEPENDENCY_MISSING = "dependency_missing"
    CONFIG_ERROR = "config_error"
    SERVER_ERROR = "server_error"
    TIMEOUT_ERROR = "timeout_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ConnectionHealth:
    """连接健康状态"""
    is_healthy: bool = False
    last_check_time: float = 0.0
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    last_success_time: float = 0.0


@dataclass
class ReconnectionConfig:
    """重连配置"""
    enabled: bool = True
    max_attempts: int = 10
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True


class MCPClient:
    """基于 fastmcp 的 MCP 客户端"""

    def __init__(self) -> None:
        self.logger = get_logger("MCPClient")

        # 基础连接属性
        self._client: Optional[FastMCPClient] = None
        self._connection_state: ConnectionState = ConnectionState.DISCONNECTED
        self._connection_health = ConnectionHealth()

        # 配置
        self.mcp_config_file: str = os.path.join(os.path.dirname(__file__), "mcp_servers.json")
        self._reconnection_config = ReconnectionConfig()
        self._connection_timeout: float = 30.0
        self._health_check_interval: float = 30.0
        self._last_config_mtime: float = 0.0

        # 任务管理
        self._reconnection_task: Optional[asyncio.Task] = None
        self._health_monitor_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

        # 兼容性属性
        self.connected = False

    @property
    def connection_state(self) -> ConnectionState:
        """获取当前连接状态"""
        return self._connection_state

    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connection_state == ConnectionState.CONNECTED

    @property
    def connection_health(self) -> ConnectionHealth:
        """获取连接健康状态"""
        return self._connection_health

    def _diagnose_connection_error(self, error: Exception) -> ConnectionErrorType:
        """诊断连接错误类型"""
        error_str = str(error).lower()
        error_type_str = type(error).__name__.lower()

        # 检查依赖缺失错误
        if "npx" in error_str and ("not found" in error_str or "not recognized" in error_str):
            return ConnectionErrorType.DEPENDENCY_MISSING

        if "npm" in error_str and ("not found" in error_str or "not recognized" in error_str):
            return ConnectionErrorType.DEPENDENCY_MISSING

        if "maicraft" in error_str and ("not found" in error_str or "cannot find" in error_str):
            return ConnectionErrorType.DEPENDENCY_MISSING

        # 检查网络错误
        if any(keyword in error_str for keyword in ["connection refused", "connection reset", "network is unreachable",
                                                   "no route to host", "connection timeout"]):
            return ConnectionErrorType.NETWORK_ERROR

        # 检查认证错误
        if any(keyword in error_str for keyword in ["authentication failed", "unauthorized", "forbidden",
                                                   "invalid credentials"]):
            return ConnectionErrorType.AUTHENTICATION_ERROR

        # 检查配置错误
        if any(keyword in error_str for keyword in ["invalid config", "configuration error", "missing config",
                                                   "config file not found"]):
            return ConnectionErrorType.CONFIG_ERROR

        # 检查超时错误
        if any(keyword in error_str for keyword in ["timeout", "timed out"]):
            return ConnectionErrorType.TIMEOUT_ERROR

        # 检查服务器错误
        if any(keyword in error_str for keyword in ["server error", "internal server error", "service unavailable"]):
            return ConnectionErrorType.SERVER_ERROR

        # 未知错误
        return ConnectionErrorType.UNKNOWN_ERROR

    def _get_error_message(self, error_type: ConnectionErrorType, original_error: str) -> str:
        """根据错误类型生成用户友好的错误消息"""
        messages = {
            ConnectionErrorType.DEPENDENCY_MISSING: (
                "依赖缺失错误：无法找到必要的工具或包。\n"
                "请检查：\n"
                "1. 是否已安装 Node.js 和 npm\n"
                "2. 是否已全局安装 maicraft 包：npm install -g maicraft@latest\n"
                "3. 是否在系统 PATH 中包含了 npx\n"
                f"原始错误：{original_error}"
            ),
            ConnectionErrorType.NETWORK_ERROR: (
                "网络连接错误：无法连接到 Minecraft 服务器。\n"
                "请检查：\n"
                "1. Minecraft 服务器是否正在运行\n"
                "2. 服务器地址和端口是否正确\n"
                "3. 防火墙是否阻止了连接\n"
                f"原始错误：{original_error}"
            ),
            ConnectionErrorType.AUTHENTICATION_ERROR: (
                "认证错误：连接被拒绝。\n"
                "请检查：\n"
                "1. 服务器是否需要认证\n"
                "2. 用户名和密码是否正确\n"
                f"原始错误：{original_error}"
            ),
            ConnectionErrorType.CONFIG_ERROR: (
                "配置错误：MCP 配置文件有问题。\n"
                "请检查：\n"
                "1. mcp_servers.json 文件是否存在\n"
                "2. 配置文件格式是否正确\n"
                f"原始错误：{original_error}"
            ),
            ConnectionErrorType.TIMEOUT_ERROR: (
                "连接超时：服务器响应超时。\n"
                "请检查：\n"
                "1. 网络连接是否稳定\n"
                "2. 服务器是否负载过高\n"
                f"原始错误：{original_error}"
            ),
            ConnectionErrorType.SERVER_ERROR: (
                "服务器错误：Minecraft 服务器内部错误。\n"
                "请检查：\n"
                "1. Minecraft 服务器状态\n"
                "2. 服务器日志中的错误信息\n"
                f"原始错误：{original_error}"
            ),
            ConnectionErrorType.UNKNOWN_ERROR: (
                f"未知连接错误：{original_error}\n"
                "请检查服务器和客户端的配置和状态。"
            )
        }
        return messages.get(error_type, f"未知错误：{original_error}")

    async def _calculate_reconnection_delay(self, attempt: int) -> float:
        """计算重连延迟时间（指数退避策略）"""
        delay = min(
            self._reconnection_config.initial_delay * (self._reconnection_config.backoff_multiplier ** attempt),
            self._reconnection_config.max_delay
        )

        if self._reconnection_config.jitter:
            import random
            delay = delay * (0.5 + random.random() * 0.5)  # 添加随机抖动

        return delay

    async def connect(self, enable_auto_reconnect: bool = True) -> bool:
        """读取 MCP JSON 配置并建立 fastmcp 客户端连接。

        Args:
            enable_auto_reconnect: 是否启用自动重连机制

        Returns:
            bool: 连接是否成功
        """
        if self._connection_state == ConnectionState.CONNECTING:
            self.logger.warning("[MCP] 连接正在进行中，请等待")
            return False

        # 更新连接状态
        self._connection_state = ConnectionState.CONNECTING
        self.logger.info("[MCP] 开始连接到 MCP 服务器...")

        try:
            # 检查配置文件是否被修改
            if os.path.exists(self.mcp_config_file):
                current_mtime = os.path.getmtime(self.mcp_config_file)
                if current_mtime != self._last_config_mtime:
                    self._last_config_mtime = current_mtime
                    self.logger.info("[MCP] 检测到配置文件变更，重新加载配置")

            # 读取配置文件
            with open(self.mcp_config_file, "r", encoding="utf-8") as f:
                config_obj = json.load(f)

        except FileNotFoundError:
            error_msg = f"MCP 配置文件不存在: {self.mcp_config_file}"
            self.logger.error(f"[MCP] {error_msg}")
            self._update_connection_state(ConnectionState.FAILED, error_msg)
            return False

        except json.JSONDecodeError as e:
            error_msg = f"MCP 配置文件格式错误: {e}"
            self.logger.error(f"[MCP] {error_msg}")
            self._update_connection_state(ConnectionState.FAILED, error_msg)
            return False

        except Exception as e:
            error_type = self._diagnose_connection_error(e)
            error_msg = self._get_error_message(error_type, str(e))
            self.logger.error(f"[MCP] 读取配置文件失败: {error_msg}")
            self._update_connection_state(ConnectionState.FAILED, error_msg)
            return False

        try:
            # 创建客户端
            self._client = FastMCPClient(config_obj)

            # 设置连接超时
            connect_task = self._client.__aenter__()
            try:
                await asyncio.wait_for(connect_task, timeout=self._connection_timeout)
            except asyncio.TimeoutError:
                raise Exception(f"连接超时 ({self._connection_timeout}秒)")

            # 更新状态
            self._update_connection_state(ConnectionState.CONNECTED)
            self.logger.info("[MCP] fastmcp 客户端已连接 (MCP JSON 配置)")

            # 获取工具列表验证连接
            tools = await self.list_available_tools()
            self.logger.info(f"[MCP] 获取工具列表成功，共 {len(tools)} 个工具")

            # 启动健康监控
            if enable_auto_reconnect:
                await self._start_health_monitor()

            return True

        except Exception as e:
            # 诊断错误类型并生成友好的错误消息
            error_type = self._diagnose_connection_error(e)
            error_msg = self._get_error_message(error_type, str(e))

            self.logger.error(f"[MCP] 连接 fastmcp 客户端失败: {error_msg}")
            self._update_connection_state(ConnectionState.FAILED, error_msg)

            # 清理失败的连接
            if self._client:
                try:
                    await self._client.__aexit__(None, None, None)
                except Exception:
                    pass
                self._client = None

            # 如果启用了自动重连，启动重连机制
            if enable_auto_reconnect and self._reconnection_config.enabled:
                self.logger.info("[MCP] 启动自动重连机制...")
                asyncio.create_task(self._start_reconnection())

            return False

    def _update_connection_state(self, state: ConnectionState, error_msg: Optional[str] = None) -> None:
        """更新连接状态并同步兼容性属性"""
        old_state = self._connection_state
        self._connection_state = state

        # 更新兼容性属性
        self.connected = (state == ConnectionState.CONNECTED)

        # 更新健康状态
        current_time = time.time()
        if state == ConnectionState.CONNECTED:
            self._connection_health.is_healthy = True
            self._connection_health.last_success_time = current_time
            self._connection_health.consecutive_failures = 0
            self._connection_health.last_error = None
        elif state == ConnectionState.FAILED:
            self._connection_health.is_healthy = False
            self._connection_health.consecutive_failures += 1
            if error_msg:
                self._connection_health.last_error = error_msg

        self._connection_health.last_check_time = current_time

        # 记录状态变更
        if old_state != state:
            self.logger.info(f"[MCP] 连接状态变更: {old_state.value} -> {state.value}")
            if error_msg:
                self.logger.debug(f"[MCP] 错误详情: {error_msg}")

    async def disconnect(self) -> None:
        """断开MCP连接并停止相关任务"""
        # 停止重连和健康监控任务
        await self._stop_background_tasks()

        # 断开客户端连接
        if self._client:
            try:
                await self._client.__aexit__(None, None, None)
            except Exception as e:
                self.logger.error(f"[MCP] 断开 fastmcp 客户端异常: {e}")

        # 清理状态
        self._client = None
        self._update_connection_state(ConnectionState.DISCONNECTED)
        self.logger.info("[MCP] fastmcp 客户端已断开")

    async def get_tools_metadata(self) -> List[Tool]:
        """列出所有可用工具的元数据（名称/描述/参数模式）。"""
        if not self._client:
            return []
        try:
            return await self._client.list_tools()
        except Exception as e:
            self.logger.error(f"[MCP] 获取工具元数据失败: {e}")
            return []

    async def call_tool_directly(self, tool_name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """直接调用工具，返回统一结构。"""

        if not self._client:
            self.logger.error("[MCP] MCP客户端未连接")
            return CallToolResult(
                content=[
                    TextContent(type="text", text="MCP 客户端未连接"),
                ],
                structured_content=None,
                is_error=True,
                data=None,
            )

        try:
            import asyncio

            if tool_name == "place_block":
                self.logger.info(f"[MCP] 调用工具: {tool_name}，参数: {arguments}")
            
            # 对需要中断的动作进行检查
            interruptible_tools = {"move", "mine_block", "place_block", "kill_mob"}
            
            if tool_name in interruptible_tools:
                # 导入全局movement来检查中断
                from agent.environment.movement import global_movement
                
                # 创建工具调用任务
                tool_task = asyncio.create_task(self._client.call_tool(tool_name, arguments))

                # 定期检查中断标志和超时
                start_time = asyncio.get_event_loop().time()
                timeout = 60.0

                while not tool_task.done():
                    # 检查超时
                    if asyncio.get_event_loop().time() - start_time > timeout:
                        tool_task.cancel()
                        self.logger.info(f"[MCP] 动作超时: {tool_name}")
                        return CallToolResult(
                            content=[
                                TextContent(type="text", text="工具调用超时"),
                            ],
                            structured_content={"timeout": True},
                            is_error=True,
                            data=None,
                        )

                    # 检查中断标志
                    if global_movement.interrupt_flag:
                        interrupt_reason = global_movement.interrupt_reason
                        global_movement.clear_interrupt()
                        tool_task.cancel()
                        self.logger.info(f"[MCP] 动作被中断: {tool_name}，原因: {interrupt_reason}")
                        return CallToolResult(
                            content=[
                                TextContent(type="text", text=f"动作被中断: {interrupt_reason}"),
                            ],
                            structured_content={"interrupt": True,"interrupt_reason": interrupt_reason},
                            is_error=True,
                            data=None,
                        )
                    # 短暂休眠，避免高CPU占用
                    await asyncio.sleep(0.1)
                
                # 工具调用正常完成
                result = tool_task.result()
                return result
            else:
                # 其他工具直接调用，不检查中断
                try:
                    result = await asyncio.wait_for(
                        self._client.call_tool(tool_name, arguments),
                        timeout=60.0,
                    )
                except asyncio.TimeoutError:
                    return CallToolResult(
                        content=[
                            TextContent(type="text", text="工具调用超时"),
                        ],
                        structured_content=None,
                        is_error=True,
                        data=None,
                    )
                return result
        except Exception as e:
            err_msg = f"[MCP] 调用工具失败: {e}"
            self.logger.error(err_msg)
            return CallToolResult(
                content=[
                    TextContent(type="text", text=err_msg),
                ],
                structured_content=None,
                is_error=True,
                data=None,
            )

    async def list_available_tools(self) -> List[str]:
        return [tool.name for tool in await self.get_tools_metadata() if tool.name]

    async def _start_health_monitor(self) -> None:
        """启动连接健康监控"""
        if self._health_monitor_task and not self._health_monitor_task.done():
            return

        self._health_monitor_task = asyncio.create_task(self._health_monitor_loop())
        self.logger.info("[MCP] 连接健康监控已启动")

    async def _stop_background_tasks(self) -> None:
        """停止所有后台任务"""
        self._shutdown_event.set()

        # 停止重连任务
        if self._reconnection_task and not self._reconnection_task.done():
            self._reconnection_task.cancel()
            try:
                await self._reconnection_task
            except asyncio.CancelledError:
                pass

        # 停止健康监控任务
        if self._health_monitor_task and not self._health_monitor_task.done():
            self._health_monitor_task.cancel()
            try:
                await self._health_monitor_task
            except asyncio.CancelledError:
                pass

        self._reconnection_task = None
        self._health_monitor_task = None
        self._shutdown_event.clear()

    async def _health_monitor_loop(self) -> None:
        """健康监控循环"""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self._health_check_interval)

                if self._shutdown_event.is_set():
                    break

                # 检查连接状态
                if self._connection_state != ConnectionState.CONNECTED:
                    continue

                # 执行健康检查
                await self._perform_health_check()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"[MCP] 健康监控异常: {e}")

    async def _perform_health_check(self) -> None:
        """执行连接健康检查"""
        try:
            # 尝试获取工具列表作为健康检查
            tools = await asyncio.wait_for(
                self.list_available_tools(),
                timeout=10.0
            )

            if tools:
                self._update_connection_state(ConnectionState.CONNECTED)
            else:
                raise Exception("获取工具列表失败")

        except Exception as e:
            self.logger.warning(f"[MCP] 健康检查失败: {e}")
            self._update_connection_state(ConnectionState.FAILED, str(e))

            # 如果启用了自动重连，启动重连
            if self._reconnection_config.enabled:
                self.logger.info("[MCP] 检测到连接异常，启动重连机制...")
                asyncio.create_task(self._start_reconnection())

    async def _start_reconnection(self) -> None:
        """启动重连机制"""
        if self._reconnection_task and not self._reconnection_task.done():
            return

        self._reconnection_task = asyncio.create_task(self._reconnection_loop())
        self.logger.info("[MCP] 重连机制已启动")

    async def _reconnection_loop(self) -> None:
        """重连循环"""
        attempt = 0

        while (not self._shutdown_event.is_set() and
               attempt < self._reconnection_config.max_attempts and
               self._connection_state != ConnectionState.CONNECTED):

            if self._shutdown_event.is_set():
                break

            attempt += 1
            self._connection_state = ConnectionState.RECONNECTING
            self.logger.info(f"[MCP] 第 {attempt}/{self._reconnection_config.max_attempts} 次重连尝试")

            try:
                # 计算延迟时间
                delay = await self._calculate_reconnection_delay(attempt - 1)
                self.logger.info(f"[MCP] 等待 {delay:.1f} 秒后重连...")
                await asyncio.sleep(delay)

                if self._shutdown_event.is_set():
                    break

                # 尝试重连
                success = await self.connect(enable_auto_reconnect=False)
                if success:
                    self.logger.info(f"[MCP] 重连成功！(第 {attempt} 次尝试)")
                    break
                else:
                    self.logger.warning(f"[MCP] 第 {attempt} 次重连失败")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"[MCP] 重连过程中发生异常: {e}")

        if attempt >= self._reconnection_config.max_attempts:
            self.logger.error(f"[MCP] 重连失败，已达到最大重试次数 ({self._reconnection_config.max_attempts})")
            self._update_connection_state(ConnectionState.FAILED, "重连失败，达到最大重试次数")

    def get_connection_status(self) -> Dict[str, Any]:
        """获取详细的连接状态信息"""
        return {
            "state": self._connection_state.value,
            "is_connected": self.is_connected,
            "health": {
                "is_healthy": self._connection_health.is_healthy,
                "last_check_time": self._connection_health.last_check_time,
                "consecutive_failures": self._connection_health.consecutive_failures,
                "last_error": self._connection_health.last_error,
                "last_success_time": self._connection_health.last_success_time
            },
            "reconnection": {
                "enabled": self._reconnection_config.enabled,
                "max_attempts": self._reconnection_config.max_attempts,
                "is_reconnecting": (self._reconnection_task is not None and not self._reconnection_task.done())
            },
            "config_file": self.mcp_config_file,
            "last_config_mtime": self._last_config_mtime
        }

    async def force_reconnect(self) -> bool:
        """强制重新连接（手动触发）"""
        self.logger.info("[MCP] 手动触发重连...")

        # 停止现有任务
        await self._stop_background_tasks()

        # 断开当前连接
        if self._client:
            try:
                await self._client.__aexit__(None, None, None)
            except Exception as e:
                self.logger.warning(f"[MCP] 断开连接时发生异常: {e}")
            self._client = None

        # 重新连接
        return await self.connect(enable_auto_reconnect=True)

    async def shutdown(self) -> None:
        """优雅关闭客户端"""
        self.logger.info("[MCP] 正在关闭 MCP 客户端...")
        await self.disconnect()
        self.logger.info("[MCP] MCP 客户端已关闭")


global_mcp_client = MCPClient()