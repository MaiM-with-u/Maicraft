from agent.block_cache.block_cache import global_block_cache
from agent.environment.environment import global_environment
from config import global_config
from openai_client.llm_request import LLMClient
from openai_client.modelconfig import ModelConfig
from agent.utils.utils import parse_json
from utils.logger import get_logger

class PlaceAction:
    def __init__(self):
        self.logger = get_logger("PlaceAction")
        model_config = ModelConfig(
            model_name=global_config.llm_fast.model,
            api_key=global_config.llm_fast.api_key,
            base_url=global_config.llm_fast.base_url,
            max_tokens=global_config.llm_fast.max_tokens,
            temperature=global_config.llm_fast.temperature
        )
        
        self.llm_client = LLMClient(model_config)
        self.logger.info("[PlaceAction] LLM客户端初始化成功")

    async def place_action(self,block_type: str, x: int, y: int, z: int):
        block_cache = global_block_cache.get_block(x, y, z)
        self_position = global_environment.block_position
        
        edit = ""
        if block_cache and block_cache.block_type != "air":
            edit += f"位置{x},{y},{z}已存在方块: {block_cache.block_type}，无法放置在{x},{y},{z}"
        if self_position.x == x and (self_position.y == y or self_position.y == y+1) and self_position.z == z:
            edit += f"你不能放置方块到你自己的脚下(x={x},y={y},z={z})或头部(x={x},y={y+1},z={z})"
        
        if edit:
            return f"无法在{x},{y},{z}放置{block_type}，理由：{edit}\n",{}
        return f"尝试在{x},{y},{z}放置{block_type}\n",{"block":block_type,"x":x,"y":y,"z":z}