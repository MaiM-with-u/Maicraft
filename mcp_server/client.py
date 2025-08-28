from __future__ import annotations

from typing import Any, Dict, List, Optional
import json
import os
from fastmcp import Client as FastMCPClient
from fastmcp.client.client import CallToolResult
from mcp.types import Tool, TextContent
from utils.logger import get_logger


class MCPClient:
    """基于 fastmcp 的 MCP 客户端"""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.logger = get_logger("MCPClient")
        self.config = config
        self.connected = False
        self._client: Optional[FastMCPClient] = None

        # 硬编码：始终使用插件 mcp 目录下的 mcp_servers.json
        # 例如: src/plugins/maicraft/mcp/mcp_servers.json
        self.mcp_config_file: str = os.path.join(os.path.dirname(__file__), "mcp_servers.json")

    async def connect(self) -> bool:
        """读取 MCP JSON 配置并建立 fastmcp 客户端连接。"""
        try:
            with open(self.mcp_config_file, "r", encoding="utf-8") as f:
                config_obj = json.load(f)
        except Exception as e:
            self.logger.error(f"[MCP] 读取配置文件失败: {e}")
            return False

        try:
            self._client = FastMCPClient(config_obj)
            # 打开会话
            await self._client.__aenter__()
            self.connected = True
            self.logger.info("[MCP] fastmcp 客户端已连接 (MCP JSON 配置)")

            # 获取工具列表
            tools = await self.list_available_tools()
            self.logger.info(f"[MCP] 获取工具列表: {tools}")

            return True
        except Exception as e:
            self.logger.error(f"[MCP] 连接 fastmcp 客户端失败: {e}")
            self._client = None
            self.connected = False
            return False

    async def disconnect(self) -> None:
        if self._client:
            try:
                await self._client.__aexit__(None, None, None)
            except Exception as e:
                self.logger.error(f"[MCP] 断开 fastmcp 客户端异常: {e}")
        self._client = None
        self.connected = False
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
            
            try:
                result = await asyncio.wait_for(
                    self._client.call_tool(tool_name, arguments),
                    timeout=120.0,  # 30秒超时
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
