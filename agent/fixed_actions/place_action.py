from agent.utils.utils import (
    parse_tool_result,
)
from agent.utils.utils_tool_translation import (
    translate_place_block_tool_result, 
)
from mcp_server.client import global_mcp_client
from agent.block_cache.block_cache import global_block_cache
from agent.environment.environment import global_environment


async def place_action(block_type: str, x: int, y: int, z: int) -> tuple[bool,bool]:
        """
        放置某个位置的方块
        block_type是方块的名称
        x,y,z是方块的坐标
        return tuple[bool,str,bool]，bool为是否成功，str为可读文本结果，bool为位置是否存在方块或实体
        """
    
        block_cache = global_block_cache.get_block(x, y, z)
        self_position = global_environment.block_position
        result_str = ""
        
        edit = ""
        if block_cache and block_cache.block_type != "air":
            edit += f"位置{x},{y},{z}已存在方块: {block_cache.block_type}，无法放置在{x},{y},{z}"
            return False,True
        if self_position.x == x and (self_position.y == y or self_position.y == y+1) and self_position.z == z:
            edit += f"你不能放置方块到你自己的脚下(x={x},y={y},z={z})或头部(x={x},y={y+1},z={z})"
            return False,True
        
        

        result_str = f"尝试在{x},{y},{z}放置{block_type}\n"
    
        args = {"block":block_type,"x":x,"y":y,"z":z}
        call_result = await global_mcp_client.call_tool_directly("place_block", args)
        is_success, result_content = parse_tool_result(call_result)
        result_str += translate_place_block_tool_result(result_content,args)
        
        return is_success,False