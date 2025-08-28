from agent.block_cache.block_cache import global_block_cache
from agent.environment import global_environment
from agent.basic_info import BlockPosition
from openai_client.llm_request import LLMClient
from openai_client.modelconfig import ModelConfig
from config import MaicraftConfig
from utils.logger import get_logger

logger = get_logger("NearbyBlockManager")


class NearbyBlockManager:
    def __init__(self,config: MaicraftConfig):
        model_config = ModelConfig(
            model_name=config.llm_fast.model,
            api_key=config.llm_fast.api_key,
            base_url=config.llm_fast.base_url,
            max_tokens=config.llm_fast.max_tokens,
            temperature=config.llm_fast.temperature
        )
        
        self.llm_client_fast = LLMClient(model_config)
        
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
        
        if block_num > 256:
            around_blocks_str = await self.get_block_details_str(position, distance)
        
        return around_blocks_str
    
    async def get_block_details_str(self, position: BlockPosition, distance: int = 5):
        """仔细观察周围方块信息"""
        around_under_feet_blocks_str = ""
        around_under_feet_blocks = self.block_cache.get_blocks_in_range(position.x, position.y, position.z, distance)

            
        if around_under_feet_blocks:
            # 合并输出：与 mix_str 统一
            grouped_positions = {}
            for block in around_under_feet_blocks:
                key = "无方块" if block.block_type == "air" else block.block_type
                if key not in grouped_positions:
                    grouped_positions[key] = []
                grouped_positions[key].append((block.position.x, block.position.y, block.position.z))
            parts = []
            for key, coords in grouped_positions.items():
                coord_str = ",".join([f"(x={x}, y={y}, z={z})" for x, y, z in coords])
                parts.append(f"{key}: {coord_str}")
            around_under_feet_blocks_str = "\n".join(parts) + "\n"
        
        # 使用LLM分析方块信息
        prompt = f"""
{global_environment.get_position_str()}

请你分析周围方块的信息，并给出分析结果。
周围方块信息: {around_under_feet_blocks_str}

请根据这些信息，用一段简短的平文本概括你脚下方块和周围方块的信息。
1. 注意当前空间大小和方块的类型，没有方块的地方是空气
2. 考虑当前所属环境，可能是矿洞，矿道，开阔区域，森林，建筑物，草原等等.....
3. 请你找出可以站立的位置，要求：有两格高空间容纳玩家，即坐标的上方一格为空气，坐标本身为空气。脚下方块不为空气，能够站立


请你根据Minecraft游戏相关知识和分析和观察时需要考虑的点给出结果

简短的分析结果:
        """
        
        # logger.info(prompt)
        
        response = await self.llm_client_fast.simple_chat(prompt)
        
        
            
            
        return response
        
        
        
        
        
        
        