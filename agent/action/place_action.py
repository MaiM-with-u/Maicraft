from agent.block_cache.block_cache import global_block_cache
from agent.environment.environment import global_environment
from mcp_server.client import global_mcp_client
from agent.utils.utils import parse_tool_result
from agent.utils.utils_tool_translation import translate_place_block_tool_result

async def place_block_action(block_type: str, x: int, y: int, z: int):
    block_cache = global_block_cache.get_block(x, y, z)
    self_position = global_environment.block_position
    
    result_str = ""
    if block_cache and block_cache.block_type != "air":
        result_str += f"位置{x},{y},{z}已存在方块: {block_cache.block_type}，无法放置在{x},{y},{z}"
        return result_str
    if self_position.x == x and (self_position.y == y or self_position.y == y+1) and self_position.z == z:
        result_str += f"你不能放置方块到你自己的脚下(x={x},y={y},z={z})或头部(x={x},y={y+1},z={z})"
        return result_str

    
    args = {"block":block_type,"x":x,"y":y,"z":z}
    call_result = await global_mcp_client.call_tool_directly("place_block", args)
    is_success, result_content = parse_tool_result(call_result)
    result_str += translate_place_block_tool_result(result_content,args)
    
    return result_str
    