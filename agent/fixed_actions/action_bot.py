from agent.fixed_actions.craft_actions import craft_item
from agent.fixed_actions.mine_actions import mine_block, mine_nearby_blocks
from agent.fixed_actions.chat_action import chat_action
from agent.fixed_actions.move_action import move_action
from agent.fixed_actions.place_action import place_action
from agent.environment.environment import global_environment
from openai_client.llm_request import LLMClient
from openai_client.modelconfig import ModelConfig
from config import global_config
from agent.fixed_actions.find_action import find_blocks, get_block
from agent.fixed_actions.view_container_action import view_container
from agent.fixed_actions.use_chest_action import use_chest
from agent.fixed_actions.use_furnace_action import use_furnace
from agent.fixed_actions.points_action import set_location_point
from agent.environment.environment_updater import EnvironmentUpdater
import asyncio

class ActionBot:
    def __init__(self):
        self.craft_item = craft_item
        self.mine_block = mine_block
        self.mine_nearby_blocks = mine_nearby_blocks
        self.chat = chat_action
        self.move = move_action
        self.place_block = place_action
        self.find_blocks = find_blocks
        self.get_block = get_block
        self.view_container = view_container
        self.use_chest = use_chest
        self.use_furnace = use_furnace
        self.set_location_point = set_location_point

        model_config = ModelConfig(
            model_name=global_config.llm.model,
            api_key=global_config.llm.api_key,
            base_url=global_config.llm.base_url,
            max_tokens=global_config.llm.max_tokens,
            temperature=global_config.llm.temperature
        )
        self.llm_client = LLMClient(model_config)
        
        
        self.environment_updater = EnvironmentUpdater()
        
        
    @property
    async def inventory(self):
        # 始终返回当前的全局背包引用
        await self.environment_updater.perform_update()
        return global_environment.inventory

    @property
    async def position(self):
        # 始终返回当前的全局位置对象
        await self.environment_updater.perform_update()
        return global_environment.block_position


bot = ActionBot()