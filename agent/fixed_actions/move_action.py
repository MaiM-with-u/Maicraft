from agent.utils.utils import (
    parse_tool_result,
)
from mcp_server.client import global_mcp_client
from agent.environment.basic_info import BlockPosition
from utils.logger import get_logger

logger = get_logger(__name__)

            
async def move_action(x: int, y: int, z: int) -> tuple[bool,BlockPosition,float]:
    args = {"x": x, "y": y, "z": z, "type": "coordinate"}
    call_result = await global_mcp_client.call_tool_directly("move", args)
    is_success, result_content = parse_tool_result(call_result)
    
    final_position_dict = result_content.get("position", {})
    if not final_position_dict:
        final_position = BlockPosition(x=x, y=y, z=z)
    else:
        logger.info(f"从 final_position 获取位置: {final_position_dict}")
        final_x = result_content.get("position", {}).get("x")
        final_y = result_content.get("position", {}).get("y")
        final_z = result_content.get("position", {}).get("z")
        final_position = BlockPosition(x=final_x, y=final_y, z=final_z)
        
    distance = result_content.get("distance")
    
    logger.info(f"移动结果: {result_content.get('position')}")
    logger.info(f"移动结果: {result_content.get('distance')}")
    
    return is_success, final_position, distance