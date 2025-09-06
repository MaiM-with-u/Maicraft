import json
import os
import time
from typing import List
from agent.common.auto_save import AutoSaveManager

class ThinkingLog:
    """思考记录"""
    def __init__(self):
        self.thinking_list:List[tuple[str,str,float]] = []
        self.auto_save_manager = AutoSaveManager("thinking_log.json", 30)
        self.auto_save_manager.set_data(self.thinking_list)
        # 启动时自动加载
        self.load_from_data_dir()
        # 启动定时保存
        self.auto_save_manager.start()
        
    def add_thinking_log(self, thinking_log: str,type:str) -> None:
        self.thinking_list.append((thinking_log,type,time.time()))
        if len(self.thinking_list) > 30:
            self.thinking_list = self.thinking_list[-30:]
        
    def get_thinking_log(self) -> str:
        # 分离不同类型的日志
        notice_items = []
        action_items = []
        thinking_items = []
        
        for item in self.thinking_list:
            log_content, log_type, timestamp = item
            if log_type == "notice":
                notice_items.append(item)
            elif log_type == "action":
                action_items.append(item)
            else:  # thinking类型
                thinking_items.append(item)
        
        # 按时间戳排序thinking记录，然后获取最新的15条
        thinking_items.sort(key=lambda x: x[2])  # 按时间戳排序
        latest_thinking = thinking_items[-2:] if len(thinking_items) > 5 else thinking_items
        
        action_items.sort(key=lambda x: x[2])  # 按时间戳排序
        latest_action = action_items[-5:] if len(action_items) > 5 else action_items
        
        # 合并所有记录并按时间排序
        all_items = notice_items + latest_action + latest_thinking
        all_items.sort(key=lambda x: x[2])  # 按时间戳排序
        
        # 构建日志字符串
        thinking_str = ""
        for item in all_items:
            time_str = time.strftime("%H:%M:%S", time.localtime(item[2]))
            log_content, log_type, _ = item
            thinking_str += f"{time_str}:{log_content}\n"
            
        return thinking_str
    
    def save_to_cache(self) -> None:
        """保存到当前目录的缓存文件"""
        self.auto_save_manager.save_to_cache()
    
    def save_to_data_dir(self) -> None:
        """保存思考记录到/data目录"""
        self.auto_save_manager.save_to_data_dir()
    
    def load_from_data_dir(self) -> bool:
        """从/data目录读取思考记录"""
        return self.auto_save_manager.load_from_data_dir()
    
    def stop(self):
        """停止自动保存线程"""
        self.auto_save_manager.stop()
    
    def __del__(self):
        """析构函数，确保线程被正确停止"""
        self.stop()

global_thinking_log = ThinkingLog()