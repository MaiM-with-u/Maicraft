from fastmcp.client.client import CallToolResult


import asyncio
from datetime import datetime
from agent.prompt_manager.prompt_manager import prompt_manager
from agent.environment.environment import global_environment
from agent.environment.environment_updater import global_environment_updater
from config import global_config
from openai_client.llm_request import LLMClient
from openai_client.modelconfig import ModelConfig
from mcp_server.client import global_mcp_client
from agent.utils.utils import parse_tool_result
from agent.utils.utils_tool_translation import translate_chat_tool_result
from agent.thinking_log import global_thinking_log
from agent.utils.utils import parse_thinking
from utils.logger import get_logger
from agent.chat_history import global_chat_history
import random

logger = get_logger("MaiChat")

class MaiChat:
    def __init__(self):
        model_config = ModelConfig(
            model_name=global_config.llm.model,
            api_key=global_config.llm.api_key,
            base_url=global_config.llm.base_url,
            max_tokens=global_config.llm.max_tokens,
            temperature=global_config.llm.temperature
        )
        
        
        self.llm_client = LLMClient(model_config)
        self.chat_task = None
        
        self.active_value = 5
        
        self.self_triggered = False
    
    async def start(self) -> None:
        """启动执行循环"""
        self.chat_task = asyncio.create_task(self.chat_loop())
    
    async def chat_loop(self):
        while True:
            await asyncio.sleep(0.5)
            if global_chat_history.called_message:
                await self.chat_when_called()
                global_chat_history.called_message = False
                self.active_value += 3
                self.self_triggered = False
            elif global_chat_history.new_message:
                if self.active_value > 0:
                    await self.chat_when_called()
                    global_chat_history.new_message = False
                    self.active_value -= 1
                    self.self_triggered = False
                elif random.random() < 0.1:
                    await self.chat_when_called()
                    global_chat_history.new_message = False
                    self.active_value += 2
                    self.self_triggered = False
            elif random.random() < 0.02 and not self.self_triggered:
                await self.chat_when_called()
                self.self_triggered = True
        
    async def chat_when_called(self):
        input_data = await global_environment.get_all_data()
        
        prompt = prompt_manager.generate_prompt("chat_mode", **input_data)

        thinking_reply = await self.llm_client.simple_chat(prompt)
        
        # logger.info(f"聊天回复: {thinking_reply}")
        
        success, _, reply_obj, thinking = parse_thinking(thinking_reply)
        if not success or not reply_obj:
            return
        
        if thinking:
            global_thinking_log.add_thinking_log(thinking_log=thinking,type = "thinking")
        
        args = {"message": reply_obj.get("message")}
        call_result: CallToolResult = await global_mcp_client.call_tool_directly("chat", args)
        is_success, result_content = parse_tool_result(call_result)

        global_thinking_log.add_thinking_log(f"发送回复: {reply_obj.get('message')}",type = "notice")
        
mai_chat = MaiChat()

        
        