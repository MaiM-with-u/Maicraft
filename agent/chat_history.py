from agent.thinking_log import global_thinking_log
from config import global_config

from utils.logger import get_logger
from agent.events import ChatEvent
from typing import List
from agent.events import global_event_store

logger = get_logger("ChatHistory")

class ChatHistory:
    def __init__(self):
        self.chat_history: List[ChatEvent] = []  # 初始化为空列表
        self.new_message: bool = False
        self.called_message: bool = False
        
    def get_chat_history_str(self) -> str:
        lines = []
        # 使用封装的方法获取最近的聊天记录（默认30分钟内，最多30条）
        recent_chats = global_event_store.get_recent_chat_events()
        for chat_event in recent_chats:
            # 使用事件对象的显示时间方法
            timestamp_str = f"[{chat_event.get_display_time()}]"

            # 替换自己的用户名为"你"，避免bot把自己当成别人
            display_name = chat_event.speaker
            if chat_event.speaker == global_config.bot.player_name:
                display_name = "你"

            lines.append(f"{timestamp_str}{display_name}: {chat_event.chat_text}")
        return "\n".join(lines)
    
    def add_chat_history(self, chat_event: ChatEvent):
        self.chat_history.append(chat_event)
        logger.info(f"添加聊天记录: {chat_event.chat_text}")
        if chat_event.speaker != global_config.bot.player_name:
            self.new_message = True
            if "麦麦" in chat_event.chat_text or global_config.bot.player_name in chat_event.chat_text or global_config.bot.player_name.lower() in chat_event.chat_text:
                # 延迟导入避免循环依赖
                global_thinking_log.add_thinking_log(f"玩家 {chat_event.speaker} 提到了你，进行回复",type = "notice")
                self.called_message = True
            else:
                global_thinking_log.add_thinking_log(f"玩家 {chat_event.speaker} 发送了消息：{chat_event.chat_text}",type = "notice")
                        
global_chat_history = ChatHistory()
