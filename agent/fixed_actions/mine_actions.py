from agent.block_cache.block_cache import global_block_cache
from agent.utils.utils import (
    parse_tool_result,
)
from agent.utils.utils_tool_translation import (
    translate_mine_nearby_tool_result, 
    translate_mine_block_tool_result, 

)
from mcp_server.client import global_mcp_client
    
async def mine_nearby_blocks(name: str, count: int) -> tuple[bool]:
    result_str = f"想要批量挖掘: {name} 数量: {count}\n"
    args = {"name": name, "count": count}
    call_result = await global_mcp_client.call_tool_directly("mine_block", args)
    is_success, result_content = parse_tool_result(call_result)
    if is_success:
        result_str += translate_mine_nearby_tool_result(result_content)
    else:
        result_str += f"批量挖掘失败: {result_content}"
        
    return is_success
    
async def mine_block(x,y,z,digOnly: bool) -> tuple[bool,bool]:
    """
    挖掘某个位置的方块
    x,y,z是方块的坐标
    digOnly是是否只挖掘，如果为True，则不收集方块
    return tuple[bool,str,bool]，bool为是否成功，bool为位置是否存在方块或方块是否可以挖掘
    """
    result_str = f"想要挖掘位置: {x},{y},{z}\n"
    block_cache = global_block_cache.get_block(x, y, z)
    if not block_cache:
        result_str += f"位置{x},{y},{z}不存在方块，无法挖掘\n"
        return False,False
    if block_cache.block_type == "air":
        result_str += f"位置{x},{y},{z}不存在方块，无法挖掘\n"
        return False,False
    if block_cache.block_type == "water" or block_cache.block_type == "lava" or block_cache.block_type == "bedrock":
        result_str += f"位置{x},{y},{z}是{block_cache.block_type}，无法挖掘\n"
        return False,False
    
    args = {"x": x, "y": y, "z": z, "digOnly": digOnly}
    call_result = await global_mcp_client.call_tool_directly("mine_block", args)
    is_success, result_content = parse_tool_result(call_result)
    if is_success:
        result_str += translate_mine_block_tool_result(result_content)
    else:
        result_str += f"挖掘失败: {result_content}"
    
    return is_success,True