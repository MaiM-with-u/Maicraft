from agent.block_cache.block_cache import global_block_cache
from agent.nearby_block import NearbyBlockManager
from agent.environment import global_environment
from agent.prompt_manager.prompt_manager import prompt_manager
from config import global_config
from openai_client.llm_request import LLMClient
from openai_client.modelconfig import ModelConfig
from agent.utils import parse_json
from utils.logger import get_logger

class MoveAction:
    def __init__(self):
        self.logger = get_logger("MoveAction")
        model_config = ModelConfig(
            model_name=global_config.llm_fast.model,
            api_key=global_config.llm_fast.api_key,
            base_url=global_config.llm_fast.base_url,
            max_tokens=global_config.llm_fast.max_tokens,
            temperature=global_config.llm_fast.temperature
        )
        
        self.nearby_block_manager = NearbyBlockManager(global_config)
        
        self.llm_client = LLMClient(model_config)
        self.logger.info("[PlaceAction] LLM客户端初始化成功")

    async def move_action(self,x: int, y: int, z: int):
        result_str = ""
        
        block_cache = global_block_cache.get_block(x, y, z)
        self_position = global_environment.block_position
        
        edit = ""
        if block_cache and block_cache.block_type != "air":
            edit += f"位置{x},{y},{z}已存在方块: {block_cache.block_type}，无法放置在{x},{y},{z}"
        if self_position.x == x and (self_position.y == y or self_position.y == y+1) and self_position.z == z:
            edit += f"你不能放置方块到你自己的脚下(x={x},y={y},z={z})或头部(x={x},y={y+1},z={z})"
        

        nearby_block_info = await self.nearby_block_manager.get_block_details_mix_str(self_position,f"{edit} 找一个适合移动的坐标")
        
        if edit:
            suggest_position = edit
        else:
            suggest_position = f"{x},{y},{z}"
        input_data = {
            "player_position": global_environment.get_position_str(),
            "nearby_block_info": nearby_block_info,
            "suggest_position": suggest_position,
            "self_area": f"自己的脚下(x={self_position.x},y={self_position.y},z={self_position.z})或头部(x={self_position.x},y={self_position.y+1},z={self_position.z})"
        }
        prompt = prompt_manager.generate_prompt("minecraft_place_block", **input_data)
        
        self.logger.info(f"[PlaceAction] 生成提示词: {prompt}")
        
        response = await self.llm_client.simple_chat(prompt)
        result_json = parse_json(response)
        
        self.logger.info(f"[PlaceAction] 解析结果: {response}")
        
        
        if not result_json:
            return result_str,{}
        
        new_x = result_json["x"]
        new_y = result_json["y"]
        new_z = result_json["z"]
        
        
        args = {"x":new_x,"y":new_y,"z":new_z}
        return f"决定移动到{new_x},{new_y},{new_z}",args