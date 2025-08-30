from typing import List, Optional
from datetime import datetime
import re
import time
import asyncio

class MinecraftMessage:
    """Minecraft聊天消息类"""
    def __init__(self, message: str, sender: str, type: str, timestamp: str):
        self.message = message
        self.sender = sender
        self.type = type
        self.timestamp = timestamp
        self.created_at = datetime.now()
    
    def __str__(self):
        return f"[{self.timestamp}] {self.sender}: {self.message}"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "message": self.message,
            "sender": self.sender,
            "type": self.type,
            "timestamp": self.timestamp,
            "created_at": self.created_at.isoformat()
        }

class ChatManager:
    """Minecraft聊天管理器"""
    
    def __init__(self, max_messages: int = 1000):
        self.message_history: List[MinecraftMessage] = []
        self.max_messages = max_messages
    
    def add_message(self, message: str, sender: str, type: str, timestamp: str):
        """添加新消息"""
        if not message or not sender:
            return
            
        # 创建新消息对象
        new_message = MinecraftMessage(message, sender, type, timestamp)
        self.message_history.append(new_message)
        
        # 限制消息历史大小
        if len(self.message_history) > self.max_messages:
            removed_count = len(self.message_history) - self.max_messages
            self.message_history = self.message_history[removed_count:]
    
    def get_message_history(self, limit: Optional[int] = None) -> List[MinecraftMessage]:
        """获取消息历史"""
        if limit is None:
            return self.message_history.copy()
        return self.message_history[-limit:] if len(self.message_history) > limit else self.message_history.copy()
    
    def get_recent_messages(self, count: int = 10) -> List[MinecraftMessage]:
        """获取最近的消息"""
        return self.get_message_history(count)
    
    def get_messages_by_sender(self, sender: str, limit: Optional[int] = None) -> List[MinecraftMessage]:
        """获取特定发送者的消息"""
        messages = [msg for msg in self.message_history if msg.sender.lower() == sender.lower()]
        if limit:
            return messages[-limit:] if len(messages) > limit else messages
        return messages
    
    def get_messages_by_type(self, msg_type: str, limit: Optional[int] = None) -> List[MinecraftMessage]:
        """获取特定类型的消息"""
        messages = [msg for msg in self.message_history if msg.type.lower() == msg_type.lower()]
        if limit:
            return messages[-limit:] if len(messages) > limit else messages
        return messages
    
    def get_message_count(self) -> int:
        """获取消息数量"""
        return len(self.message_history)

global_chat_manager = ChatManager()