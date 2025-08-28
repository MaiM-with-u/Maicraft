from typing import Dict, List, Any, Optional, Callable, Coroutine
from langchain_core.tools import BaseTool, Tool
from utils.logger import get_logger
from mcp_server.client import MCPClient
from mcp.types import Tool as McpTool, TextContent
from fastmcp.client.client import CallToolResult
import dirtyjson


class MCPToolAdapter:
    """将MCP工具转换为LangChain Tool"""

    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
        self.logger = get_logger("MCPToolAdapter")
        self._tools_cache: Optional[List[BaseTool]] = None
        self._tools_metadata_cache: Optional[List[McpTool]] = None


    async def create_langchain_tools(self) -> List[BaseTool]:
        """将MCP工具转换为LangChain Tool列表"""
        if self._tools_cache is not None:
            return self._tools_cache

        try:
            self.logger.info("[MCP工具适配器] 开始获取MCP工具列表")

            # 获取MCP工具列表
            tools_info = await self._get_mcp_tools()
            if not tools_info:
                self.logger.warning("[MCP工具适配器] 未获取到MCP工具")
                return []

            # 缓存工具元数据
            self._tools_metadata_cache = tools_info

            langchain_tools = []
            for tool_info in tools_info:
                try:
                    tool = await self._create_langchain_tool(tool_info)
                    if tool:
                        langchain_tools.append(tool)
                        self.logger.info(f"[MCP工具适配器] 成功创建工具: {tool.name}")
                except Exception as e:
                    self.logger.error(f"[MCP工具适配器] 创建工具失败 {tool_info.name}: {e}")

            self._tools_cache = langchain_tools
            self.logger.info(f"[MCP工具适配器] 成功创建 {len(langchain_tools)} 个LangChain工具")
            return langchain_tools

        except Exception as e:
            self.logger.error(f"[MCP工具适配器] 创建LangChain工具失败: {e}")
            return []

    async def _get_mcp_tools(self) -> List[McpTool]:
        """获取MCP工具信息"""
        try:
            self.logger.info("[MCP工具适配器] 获取MCP工具信息")

            # 使用MCP客户端的get_tools_metadata方法
            if hasattr(self.mcp_client, "get_tools_metadata"):
                tools_info = await self.mcp_client.get_tools_metadata()
                self.logger.info(f"[MCP工具适配器] 获取到 {len(tools_info)} 个MCP工具")
                return tools_info
            else:
                self.logger.warning("[MCP工具适配器] MCP客户端不支持get_tools_metadata方法")
                return []

        except Exception as e:
            self.logger.error(f"[MCP工具适配器] 获取MCP工具信息失败: {e}")
            return []

    async def _create_langchain_tool(self, tool_info: McpTool) -> Optional[BaseTool]:
        """创建单个LangChain工具"""
        try:
            name = tool_info.name
            description = tool_info.description or ""
            schema = tool_info.inputSchema

            if not name:
                self.logger.warning("[MCP工具适配器] 工具名称为空，跳过")
                return None

            # 生成包含参数信息的详细描述
            detailed_description = self._generate_detailed_description(name, description, schema)

            # 创建工具执行函数
            tool_func = self._create_tool_function(name)

            # 创建同步包装器
            def sync_wrapper(input_json: str) -> str:
                import asyncio

                try:
                    # 获取当前事件循环或创建新的
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                    # 运行异步函数
                    result = loop.run_until_complete(tool_func(input_json))

                    return result.content[0].text  # type: ignore
                except Exception as e:
                    err_msg = f"[MCP工具适配器] 工具执行异常 {name}: {e}"
                    self.logger.error(err_msg)
                    return err_msg

            # 使用Tool创建LangChain工具（不需要args_schema）
            langchain_tool = Tool(name=name, description=detailed_description, func=sync_wrapper)

            return langchain_tool

        except Exception as e:
            self.logger.error(f"[MCP工具适配器] 创建工具 {tool_info.name} 失败: {e}")
            return None

    def _create_tool_model(self, name: str, schema: McpTool) -> type:
        """根据MCP schema动态创建Pydantic模型"""
        try:
            # 对于ZeroShotAgent，我们需要创建单输入工具
            # 将所有参数合并为一个JSON字符串输入
            from pydantic import BaseModel, Field
            from typing import Annotated

            # 创建一个通用的输入模型类
            class GenericInputModel(BaseModel):
                input_json: Annotated[
                    str, Field(description="JSON格式的输入参数，包含所有必需和可选的参数", default="{}")
                ]

            # 动态设置类名
            GenericInputModel.__name__ = f"{name.capitalize()}Input"
            self.logger.debug(f"[MCP工具适配器] 创建单输入模型类: {name.capitalize()}Input")
            return GenericInputModel

        except Exception as e:
            self.logger.error(f"[MCP工具适配器] 创建模型类失败 {name}: {e}")
            # 返回默认模型
            from pydantic import BaseModel, Field
            from typing import Annotated

            class DefaultInputModel(BaseModel):
                input_json: Annotated[str, Field(default="{}", description="JSON格式的输入参数")]

            DefaultInputModel.__name__ = f"{name.capitalize()}Input"
            return DefaultInputModel

    def _convert_schema_type(self, schema_type: str) -> type:
        """转换JSON schema类型到Python类型"""
        type_mapping = {"string": str, "integer": int, "number": float, "boolean": bool, "array": List, "object": Dict}
        return type_mapping.get(schema_type, str)

    def _get_tool_metadata(self, tool_name: str) -> Optional[McpTool]:
        """获取指定工具的元数据"""
        if not self._tools_metadata_cache:
            return None

        return next(
            (tool_info for tool_info in self._tools_metadata_cache if tool_info.name == tool_name),
            None,
        )

    def _generate_detailed_description(self, name: str, description: str, schema: Dict[str, Any]) -> str:
        """生成包含参数信息的详细工具描述"""
        detailed_desc = f"{description}\n\n"

        if schema:
            properties = schema.get("properties", {})
            required_fields = schema.get("required", [])

            if properties:
                detailed_desc += "参数说明:\n"

                for field_name, field_info in properties.items():
                    field_type = field_info.get("type", "unknown")
                    field_desc = field_info.get("description", "")
                    is_required = field_name in required_fields
                    default_value = field_info.get("default")

                    # 构建参数描述
                    param_desc = f"- {field_name} ({field_type})"
                    param_desc += " [必需]" if is_required else " [可选]"
                    if field_desc:
                        param_desc += f": {field_desc}"

                    if default_value is not None and not is_required:
                        param_desc += f" (默认值: {default_value})"

                    detailed_desc += param_desc + "\n"

        return detailed_desc.strip()

    def _validate_and_fix_parameters(self, tool_name: str, parsed_args: Dict[str, Any]) -> Dict[str, Any]:
        """基于工具元数据验证和修复参数"""
        tool_metadata = self._get_tool_metadata(tool_name)
        if not tool_metadata:
            self.logger.warning(f"[MCP工具适配器] 未找到工具 {tool_name} 的元数据，跳过参数验证")
            return parsed_args

        schema = tool_metadata.inputSchema
        properties = schema.get("properties", {})
        required_fields = schema.get("required", [])

        self.logger.info(f"[MCP工具适配器] 验证工具 {tool_name} 的参数, 必需字段: {required_fields}, 可选字段: {list(properties.keys())}, 传入参数: {list(parsed_args.keys())}")

        # 检查必需字段
        missing_required = []
        missing_required.extend(field for field in required_fields if field not in parsed_args)
        if missing_required:
            self.logger.warning(f"[MCP工具适配器] 工具 {tool_name} 缺少必需字段: {missing_required}")

            # 尝试使用默认值
            for field in missing_required:
                if field in properties:
                    default_value = properties[field].get("default")
                    if default_value is not None:
                        parsed_args[field] = default_value
                        self.logger.info(f"[MCP工具适配器] 使用默认值: {field} = {default_value}")

        return parsed_args

    def _create_tool_function(self, tool_name: str) -> Callable[[str], Coroutine[Any, Any, CallToolResult]]:
        """创建工具执行函数"""

        async def tool_function(input_json: str) -> CallToolResult:
            """工具执行函数"""
            try:
                self.logger.info(f"[MCP工具适配器] 执行工具: {tool_name}, 参数: {input_json}")

                # 解析JSON输入参数
                try:
                    if input_json.strip():
                        # 使用dirty-json库自动修复和解析JSON
                        try:
                            parsed_args = dirtyjson.loads(input_json)
                            self.logger.debug(f"[MCP工具适配器] 使用dirty-json成功解析参数: {parsed_args}")
                        except Exception as e:
                            self.logger.warning(f"[MCP工具适配器] dirty-json解析失败: {e}")
                            parsed_args = {}
                    else:
                        parsed_args = {}

                    self.logger.info(f"[MCP工具适配器] 解析后的参数: {parsed_args}")
                except Exception as e:
                    self.logger.warning(f"[MCP工具适配器] 参数解析失败 {tool_name}: {e}")
                    parsed_args = {}

                # 基于工具元数据验证和修复参数
                if isinstance(parsed_args, dict):
                    parsed_args = self._validate_and_fix_parameters(tool_name, parsed_args)

                # 检查MCP客户端状态
                if not self.mcp_client:
                    self.logger.error("[MCP工具适配器] MCP客户端为空")
                    return CallToolResult(
                        content=[TextContent(type="text", text="MCP客户端为空")],
                        structured_content={},
                        is_error=True,
                        data={},
                    )

                # 使用MCP客户端的call_tool_directly方法
                self.logger.info(f"[MCP工具适配器] 准备调用MCP工具: {tool_name}")
                return await self.mcp_client.call_tool_directly(tool_name, parsed_args)

            except Exception as e:
                self.logger.error(f"[MCP工具适配器] 工具执行失败 {tool_name}: {e}")
                return CallToolResult(
                    content=[TextContent(type="text", text=str(e))],
                    structured_content={},
                    is_error=True,
                    data={},
                )

        return tool_function

    def clear_cache(self):
        """清除工具缓存"""
        self._tools_cache = None
        self.logger.info("[MCP工具适配器] 清除工具缓存")
