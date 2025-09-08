"""
寻找方块动作实现
"""
import math
from utils.logger import get_logger
from agent.environment.environment import global_environment
from mcp_server.client import global_mcp_client
from agent.utils.utils import parse_tool_result
from agent.block_cache.block_cache import global_block_cache
from agent.common.basic_class import BlockPosition

logger = get_logger("find_block_action")


async def find_block_action(block_type: str, radius: float = 16.0) -> str:
    """
    寻找指定半径内 canSee 的方块
    
    Args:
        block_type: 要寻找的方块类型
        radius: 搜索半径（默认16格）
        
    Returns:
        找到的方块信息文本
    """
    try:
        if radius > 128:
            radius = 128
        
        # 获取玩家当前位置
        if not global_environment.block_position:
            return "无法获取玩家当前位置"
        
        player_pos = global_environment.block_position
        
        # 计算查询区域
        half_size = int(math.ceil(radius))
        start_x = player_pos.x - half_size
        start_y = player_pos.y - half_size
        start_z = player_pos.z - half_size
        end_x = player_pos.x + half_size
        end_y = player_pos.y + half_size
        end_z = player_pos.z + half_size
        
        # 调用 query_area_blocks 工具
        call_result = await global_mcp_client.call_tool_directly("query_area_blocks", {
            "startX": start_x,
            "startY": start_y,
            "startZ": start_z,
            "endX": end_x,
            "endY": end_y,
            "endZ": end_z,
            "useRelativeCoords": False,
            "maxBlocks": 5000,
            "compressionMode": True,
            "includeBlockCounts": False
        })
        
        # 解析工具结果
        is_success, result_content = parse_tool_result(call_result)
        if not is_success:
            return f"查询方块失败: {result_content}"
        
        # 处理查询结果
        found_blocks = []
        if isinstance(result_content, dict):
            compressed_blocks = result_content.get("compressedBlocks", [])
            
            for block_data in compressed_blocks:
                current_block_type = block_data.get("name", "")
                if current_block_type != block_type:
                    continue
                    
                can_see = block_data.get("canSee", False)
                if not can_see:
                    continue
                    
                positions = block_data.get("positions", [])
                for pos in positions:
                    x = pos.get("x", 0)
                    y = pos.get("y", 0)
                    z = pos.get("z", 0)
                    
                    # 计算与玩家的距离
                    dx = x - player_pos.x
                    dy = y - player_pos.y
                    dz = z - player_pos.z
                    distance = math.sqrt(dx*dx + dy*dy + dz*dz)
                    
                    # 检查是否在半径内
                    if distance <= radius:
                        # 添加到方块缓存中
                        block_pos = BlockPosition(x=x, y=y, z=z)
                        global_block_cache.add_block(block_type, True, block_pos)
                        
                        found_blocks.append({
                            'position': (x, y, z),
                            'distance': distance
                        })
        
        # 按距离排序
        found_blocks.sort(key=lambda x: x['distance'])
        
        # 生成结果文本
        if not found_blocks:
            return f"在半径 {radius} 格内未找到可见的 {block_type} 方块"
        
        result_lines = [f"在半径 {radius} 格内找到 {len(found_blocks)} 个可见的 {block_type} 方块:"]
        
        for i, block_info in enumerate(found_blocks[:10]):  # 最多显示10个
            x, y, z = block_info['position']
            distance = block_info['distance']
            result_lines.append(f"  {i+1}. 位置 ({x}, {y}, {z}) 距离 {distance:.1f} 格")
        
        if len(found_blocks) > 10:
            result_lines.append(f"  ... 还有 {len(found_blocks) - 10} 个方块未显示")
        
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"寻找方块时出错: {e}")
        return f"寻找方块时出错: {e}"