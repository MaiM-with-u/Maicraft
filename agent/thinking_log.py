import json
import os
import time
from typing import List
from agent.events import global_event_store

class ThinkingLog:
    """思考记录"""
    def __init__(self):
        self.thinking_list:List[tuple[str,str,float]] = []
        self.data_file = "data/thinking_log.json"
        self.judge_guidance:str = ""
        # 确保data目录存在
        os.makedirs("data", exist_ok=True)
        # 启动时自动加载
        self.load_from_json()
        
    def set_judge_guidance(self, judge_guidance:str) -> None:
        self.judge_guidance = judge_guidance
    
    def add_thinking_log(self, thinking_log: str,type:str) -> None:
        self.thinking_list.append((thinking_log,type,time.time()))
        # 限制总日志数量为50条
        if len(self.thinking_list) > 20:
            self.thinking_list = self.thinking_list[-20:]
        # 保存到JSON文件
        self.save_to_json()
        
    def clear_thinking_log(self) -> None:
        self.thinking_list = []
        self.save_to_json()
        
    def get_thinking_log(self) -> str:
        # 分离不同类型的日志
        notice_items = []
        action_items = []
        event_items = []
        thinking_items = []
        
        for item in self.thinking_list:
            log_content, log_type, timestamp = item
            if log_type == "notice":
                notice_items.append(item)
            elif log_type == "action":
                action_items.append(item)
            elif log_type == "event":
                # 跳过原有的事件日志，现在从event_store获取
                pass
            else:  # thinking类型
                thinking_items.append(item)
        
        # 从event_store获取最新的游戏事件
        recent_events = global_event_store.get_recent_events(15)
        for event in recent_events:
            event_items.append((str(event), "event", event.timestamp))
        
        # 按时间戳排序并获取最新记录
        thinking_items.sort(key=lambda x: x[2])
        latest_thinking = thinking_items[-3:] if len(thinking_items) > 3 else thinking_items
        
        action_items.sort(key=lambda x: x[2])
        latest_action = action_items[-8:] if len(action_items) > 8 else action_items

        event_items.sort(key=lambda x: x[2])
        latest_event = event_items[-5:] if len(event_items) > 5 else event_items
        
        notice_items.sort(key=lambda x: x[2])
        latest_notice = notice_items[-8:] if len(notice_items) > 8 else notice_items
        
        # 合并所有记录并按时间排序
        all_items = latest_notice + latest_action + latest_thinking + latest_event
        all_items.sort(key=lambda x: x[2])  # 按时间戳排序
        
        # 构建日志字符串
        thinking_str = ""
        for item in all_items:
            # 处理时间戳格式转换（毫秒转秒）
            timestamp = item[2]
            if isinstance(timestamp, (int, float)) and timestamp > 1e10:
                # 如果是毫秒级时间戳，转换为秒级
                timestamp = timestamp / 1000.0

            time_str = time.strftime("%H:%M:%S", time.localtime(timestamp))
            log_content, log_type, _ = item
            thinking_str += f"{time_str}:{log_content}\n"

        return thinking_str


    def get_thinking_log_full(self) -> str:
        # 分离不同类型的日志
        notice_items = []
        action_items = []
        event_items = []
        thinking_items = []
        
        for item in self.thinking_list:
            log_content, log_type, timestamp = item
            if log_type == "notice":
                notice_items.append(item)
            elif log_type == "action":
                action_items.append(item)
            elif log_type == "event":
                # 跳过原有的事件日志，现在从event_store获取
                pass
            else:  # thinking类型
                thinking_items.append(item)
        
        # 从event_store获取更多的游戏事件
        recent_events = global_event_store.get_recent_events(20)
        for event in recent_events:
            event_items.append((str(event), "event", event.timestamp))
        
        # 按时间戳排序并获取最新记录
        thinking_items.sort(key=lambda x: x[2])
        latest_thinking = thinking_items[-10:] if len(thinking_items) > 10 else thinking_items
        
        action_items.sort(key=lambda x: x[2])
        latest_action = action_items[-10:] if len(action_items) > 10 else action_items

        event_items.sort(key=lambda x: x[2])
        latest_event = event_items[-10:] if len(event_items) > 10 else event_items
        
        notice_items.sort(key=lambda x: x[2])
        latest_notice = notice_items[-10:] if len(notice_items) > 10 else notice_items
        
        # 合并所有记录并按时间排序
        all_items = latest_notice + latest_action + latest_thinking + latest_event
        all_items.sort(key=lambda x: x[2])  # 按时间戳排序

        # 构建日志字符串
        thinking_str = ""
        for item in all_items:
            # 使用统一的工具函数处理时间戳转换
            from utils.timestamp_utils import format_timestamp_for_display
            time_str = format_timestamp_for_display(item[2])
            log_content, log_type, _ = item
            thinking_str += f"{time_str}:{log_content}\n"

        return thinking_str
    
    def save_to_json(self) -> None:
        """保存思考记录到JSON文件"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.thinking_list, f, ensure_ascii=False, indent=2)
    
    def load_from_json(self) -> None:
        """从JSON文件读取思考记录"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.thinking_list = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                # 文件不存在或格式错误时，使用空列表
                self.thinking_list = []

global_thinking_log = ThinkingLog()