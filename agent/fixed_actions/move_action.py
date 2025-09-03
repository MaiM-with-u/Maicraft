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
    # result_content 已经是字典类型，不需要 json.loads()
    logger.info(f"移动结果: {result_content}")
    logger.info(f"移动结果: {type(result_content)}")
    x = result_content.get("final_position", {}).get("x")
    y = result_content.get("final_position", {}).get("y")
    z = result_content.get("final_position", {}).get("z")
    final_position = BlockPosition(x=x, y=y, z=z)
    distance = result_content.get("distance")
    
    
    logger.info(f"移动结果: {result_content.get('final_position')}")
    logger.info(f"移动结果: {result_content.get('distance')}")
    
    return is_success, final_position, distance