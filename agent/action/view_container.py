from config import global_config
from agent.block_cache.block_cache import global_block_cache
from agent.utils.utils import parse_tool_result

class ViewContainer:
    def __init__(self, mcp_client):
        self.mcp_client = mcp_client

    async def view_chest(self, x, y, z):
        block_cache = global_block_cache.get_block(x, y, z)
        if block_cache.block_type != "chest":
            return f"位置{x},{y},{z}不是箱子，无法查看{block_cache.block_type}"
        
        args = {"x": x, "y": y, "z": z,"includeContainerInfo": True}
        call_result = await self.mcp_client.call_tool_directly("query_block", args)
        is_success, result_content = parse_tool_result(call_result)
        
        if not is_success:
            return f"查看箱子失败: {result_content}"
        
        return result_content