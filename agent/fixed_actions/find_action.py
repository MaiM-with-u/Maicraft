from agent.utils.utils import (
    parse_tool_result,
)
from agent.utils.utils_tool_translation import (
    translate_chat_tool_result, 

)
from agent.block_cache.block_cache import Block
from agent.block_cache.block_cache import global_block_cache
from agent.environment.environment import global_environment

async def find_blocks(block_type: str, radius: float) -> tuple[bool,list[Block]]:
    if radius > 32:
        radius = 32
    position =global_environment.block_position
    blocks = global_block_cache.find_blocks_in_range(block_type, position.x, position.y, position.z, radius)
    result_str = ""
    for block in blocks:
        result_str += f"位置{block.position.x},{block.position.y},{block.position.z}的方块是{block.block_type}\n"
        
    return True, blocks

async def get_block(x: int, y: int, z: int) -> Block:
    block = global_block_cache.get_block(x, y, z)
    if block:
        return block
    return None