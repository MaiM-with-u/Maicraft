"""
MCP工具管理REST API路由
提供MCP工具元数据获取和工具调用功能
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..models.responses import ApiResponse

# 导入MCP客户端
try:
    from ...mcp_server.client import global_mcp_client
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from mcp_server.client import global_mcp_client


# 创建路由器
mcp_router = APIRouter(prefix="/api/mcp", tags=["mcp"])


class ToolCallRequest(BaseModel):
    """工具调用请求模型"""
    tool_name: str
    arguments: Dict[str, Any]


@mcp_router.get("/tools", response_model=ApiResponse)
async def get_tools_metadata():
    """获取所有可用MCP工具的元数据信息"""
    try:
        # 检查MCP客户端是否连接
        if not global_mcp_client.connected:
            return ApiResponse(
                isSuccess=False,
                message="MCP_NOT_CONNECTED: MCP客户端未连接",
                data=None
            )

        # 获取工具元数据
        tools = await global_mcp_client.get_tools_metadata()

        # 转换为API响应格式
        tools_data = []
        for tool in tools:
            tool_info = {
                "name": tool.name,
                "description": tool.description if hasattr(tool, 'description') else "",
                "inputSchema": tool.inputSchema if hasattr(tool, 'inputSchema') else {}
            }
            tools_data.append(tool_info)

        return ApiResponse(
            isSuccess=True,
            message="获取工具元数据成功",
            data={
                "tools": tools_data,
                "total": len(tools_data)
            }
        )

    except Exception as e:
        return ApiResponse(
            isSuccess=False,
            message=f"INTERNAL_ERROR: 获取工具元数据失败: {str(e)}",
            data=None
        )


@mcp_router.post("/tools/call", response_model=ApiResponse)
async def call_tool(request: ToolCallRequest):
    """直接调用指定的MCP工具"""
    try:
        # 检查MCP客户端是否连接
        if not global_mcp_client.connected:
            return ApiResponse(
                isSuccess=False,
                message="MCP_NOT_CONNECTED: MCP客户端未连接",
                data=None
            )

        # 验证工具名称
        if not request.tool_name:
            return ApiResponse(
                isSuccess=False,
                message="VALIDATION_ERROR: 工具名称不能为空",
                data={"field": "tool_name", "reason": "工具名称不能为空"}
            )

        # 调用工具
        result = await global_mcp_client.call_tool_directly(
            request.tool_name,
            request.arguments or {}
        )

        # 处理结果
        if result.is_error:
            # 工具调用失败
            return ApiResponse(
                isSuccess=False,
                message=f"TOOL_ERROR: {result.content[0].text if result.content else '工具调用失败'}",
                data={
                    "tool_name": request.tool_name,
                    "arguments": request.arguments,
                    "result": {
                        "content": [content.__dict__ if hasattr(content, '__dict__') else content for content in result.content] if result.content else [],
                        "structured_content": result.structured_content,
                        "is_error": result.is_error,
                        "data": result.data
                    }
                }
            )
        else:
            # 工具调用成功
            return ApiResponse(
                isSuccess=True,
                message="工具调用成功",
                data={
                    "tool_name": request.tool_name,
                    "arguments": request.arguments,
                    "result": {
                        "content": [content.__dict__ if hasattr(content, '__dict__') else content for content in result.content] if result.content else [],
                        "structured_content": result.structured_content,
                        "is_error": result.is_error,
                        "data": result.data
                    }
                }
            )

    except Exception as e:
        return ApiResponse(
            isSuccess=False,
            message=f"INTERNAL_ERROR: 工具调用失败: {str(e)}",
            data={
                "tool_name": request.tool_name,
                "arguments": request.arguments
            }
        )
