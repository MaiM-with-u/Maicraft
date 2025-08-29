from agent.block_cache.block_cache import global_block_cache
from agent.environment.basic_info import BlockPosition

from utils.logger import get_logger

logger = get_logger("NearbyBlockManager")


class NearbyBlockManager:
    def __init__(self):
        self.block_cache = global_block_cache
    
    async def get_block_details_mix_str(self, position: BlockPosition, distance: int = 4):
        around_blocks = self.block_cache.get_blocks_in_range(position.x, position.y, position.z, distance)
        block_num = 0
        # 分组：key 为展示名称（空气 -> 无方块，其它直接用方块类型）
        grouped_positions = {}
        
        for block in around_blocks:
            block_num += 1
            key = "无方块" if block.block_type == "air" else block.block_type
            if key not in grouped_positions:
                grouped_positions[key] = []
            grouped_positions[key].append((block.position.x, block.position.y, block.position.z))
        
        # 组装输出：同类方块在同一行内以坐标列表形式展示
        parts = []
        for key, coords in grouped_positions.items():
            coord_str = ",".join([f"(x={x}, y={y}, z={z})" for x, y, z in coords])
            parts.append(f"{key}: {coord_str}")
        
        around_blocks_str = "\n".join(parts) + "\n"
        around_blocks_str += f"玩家所在位置: x={position.x}, y={position.y}, z={position.z}\n"
        around_blocks_str += f"玩家头部位置: x={position.x}, y={position.y+1}, z={position.z}\n"
        
        return around_blocks_str

        
        
        
        
        
        
        