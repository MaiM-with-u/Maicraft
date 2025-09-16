"""
聊天事件实现
"""
from dataclasses import dataclass
from typing import Optional
from ..base_event import BaseEvent


@dataclass
class ChatEvent(BaseEvent):
    """聊天事件"""
    chat_text: str = ""
    
    def get_description(self) -> str:
        return f"{self.player_name}说: {self.chat_text}"
    
    def to_dict(self) -> dict:
        result = super().to_dict()
        result["chat_text"] = self.chat_text
        return result
