from typing import List, Optional
from datetime import datetime
import asyncio
from agent.chat_manager import global_chat_manager
class MaiChat:
    """Mai聊天"""
    def __init__(self):
        self.last_message_time = 0
        self.last_message_count = 0
    
    def add_message(self, message: str, sender: str, type: str, timestamp: str):
        global_chat_manager.add_message(message, sender, type, timestamp)
        
    def check_if_new_message(self):
        """检查有没有新消息"""
        message_count = global_chat_manager.get_message_count()
        if message_count > self.last_message_count:
            self.last_message_count = message_count
            return True
        return False
        
        
    async def chat(self):
        """聊天"""
        while True:
            if self.check_if_new_message():
                pass
            await asyncio.sleep(1)