from agent.environment.locations import global_location_points
from agent.environment.environment import global_environment
from agent.environment.basic_info import BlockPosition
from agent.utils.utils import calculate_distance,parse_tool_result
from utils.logger import get_logger
from mcp_server.client import global_mcp_client

logger = get_logger("MoveAction")

async def move_to_position(x:int,y:int,z:int):
    result_str = ""
    args = {"x": x, "y": y, "z": z, "type": "coordinate"}
    call_result = await global_mcp_client.call_tool_directly("move", args)
    
    is_success, result_content = parse_tool_result(call_result)
    
    
    
    if isinstance(result_content, str):
        # 如果失败
        final_position = global_environment.block_position
        distance = calculate_distance(final_position, BlockPosition(x=x, y=y, z=z))
        result_str = f"未移动到目标点，最终位置{final_position}，距离目标点{distance}"
    else:
        
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
        result_str = f"移动最终位置{final_position}，距离目标点{distance}"

    return result_str
    
async def go_to_location(location_name:str):
    location = global_location_points.get_location(location_name)
    if not location:
        return f"坐标点{location_name}不存在",{}
    else:
        logger.info(f"决定移动到坐标点{location_name}，坐标{location.x},{location.y},{location.z}")
        return await move_to_position(location.x,location.y,location.z)