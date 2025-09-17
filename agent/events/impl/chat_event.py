"""
聊天事件实现
"""
from dataclasses import dataclass
from typing import Optional
from ..base_event import BaseEvent


class ChatEvent(BaseEvent):
    """聊天事件"""

    def __init__(self, type: str, gameTick: int, timestamp: float, speaker: str = "", chat_text: str = ""):
        """初始化聊天事件"""
        super().__init__(type, gameTick, timestamp)
        self.speaker = speaker  # 说话人
        self.chat_text = chat_text

    def get_description(self) -> str:
        return f"{self.speaker}说: {self.chat_text}"

    def to_context_string(self) -> str:
        return f"[chat] {self.speaker}: {self.chat_text}"

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["chat_text"] = self.chat_text
        result["speaker"] = self.speaker
        return result

    @classmethod
    def from_raw_data(cls, event_data_item: dict) -> 'ChatEvent':
        """从原始数据创建聊天事件"""
        chat_info = event_data_item.get("chatInfo", {})
        return cls(
            type="chat",
            gameTick=event_data_item.get("gameTick", 0),
            timestamp=event_data_item.get("timestamp", 0),
            speaker=chat_info.get("username", ""),
            chat_text=chat_info.get("text", "")
        )
