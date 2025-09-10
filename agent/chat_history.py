from datetime import datetime
from agent.thinking_log import global_thinking_log

from utils.logger import get_logger
from agent.common.basic_class import Event
from typing import List, Optional
import asyncio


logger = get_logger("ChatHistory")

class ChatHistory:
    def __init__(self):
        self.chat_history: List[Event] = []  # 初始化为空列表
        self.new_message: bool = False
        self.called_message: bool = False
        
    def get_chat_history_str(self) -> str:
        lines = []
        # 只获取最近30分钟以内的聊天记录
        current_time = datetime.now().timestamp()
        recent_chats = []
        for chat_event in self.chat_history:
            if current_time - chat_event.timestamp <= 1800:  # 30分钟 = 1800秒
                recent_chats.append(chat_event)
        for chat_event in recent_chats:
            dt = datetime.fromtimestamp(chat_event.timestamp)
            timestamp_str = f"[{dt.strftime('%H:%M:%S')}]"
            lines.append(f"{timestamp_str}{chat_event.player_name}: {chat_event.chat_text}")
        return "\n".join(lines)
    
    def add_chat_history(self, chat_event: Event):
        self.chat_history.append(chat_event)
        logger.info(f"添加聊天记录: {chat_event.chat_text}")
        if chat_event.player_name != "Mai":
            self.new_message = True
            if "麦麦" in chat_event.chat_text or "Mai" in chat_event.chat_text or "mai" in chat_event.chat_text:
                # 延迟导入避免循环依赖
                global_thinking_log.add_thinking_log(f"玩家 {chat_event.player_name} 提到了你，进行回复",type = "notice")
                self.called_message = True
            else:
                global_thinking_log.add_thinking_log(f"玩家 {chat_event.player_name} 发送了消息：{chat_event.chat_text}",type = "notice")
                        
global_chat_history = ChatHistory()
