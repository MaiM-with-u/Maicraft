import json
import os
import threading
import time
from typing import List

class ThinkingLog:
    """思考记录"""
    def __init__(self):
        self.thinking_list:List[tuple[str,str,float]] = []
        self._stop_event = threading.Event()
        self._auto_save_thread = None
        # 启动时自动加载
        self.load_from_data_dir()
        # 启动定时保存
        self._start_auto_save()
        
    def add_thinking_log(self, thinking_log: str,type:str) -> None:
        self.thinking_list.append((thinking_log,type,time.time()))
        if len(self.thinking_list) > 20:
            self.thinking_list = self.thinking_list[-20:]
        
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
        latest_thinking = thinking_items[-2:] if len(thinking_items) > 2 else thinking_items
        
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
        with open("thinking_log.json", "w", encoding="utf-8") as f:
            json.dump(self.thinking_list, f, ensure_ascii=False, indent=2)
    
    def save_to_data_dir(self) -> None:
        """保存思考记录到/data目录"""
        data_dir = "data"
        # 确保data目录存在
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        file_path = os.path.join(data_dir, "thinking_log.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.thinking_list, f, ensure_ascii=False, indent=2)
    
    def load_from_data_dir(self) -> bool:
        """从/data目录读取思考记录"""
        data_dir = "data"
        file_path = os.path.join(data_dir, "thinking_log.json")
        
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.thinking_list = json.load(f)
                return True
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"读取思考记录失败: {e}")
                return False
        else:
            print(f"思考记录文件不存在: {file_path}")
            return False
    
    def _start_auto_save(self):
        """启动自动保存线程，每30秒保存一次"""
        def auto_save_worker():
            while not self._stop_event.is_set():
                # 等待30秒或者直到收到停止信号
                if self._stop_event.wait(30):
                    break
                try:
                    self.save_to_data_dir()
                    print("思考记录已自动保存")
                except Exception as e:
                    print(f"自动保存思考记录失败: {e}")
        
        # 启动后台线程
        self._auto_save_thread = threading.Thread(target=auto_save_worker, daemon=True)
        self._auto_save_thread.start()
    
    def stop(self):
        """停止自动保存线程"""
        if self._stop_event and not self._stop_event.is_set():
            self._stop_event.set()
            if self._auto_save_thread and self._auto_save_thread.is_alive():
                self._auto_save_thread.join(timeout=2)  # 等待最多2秒
                print("思考记录自动保存线程已停止")
    
    def __del__(self):
        """析构函数，确保线程被正确停止"""
        self.stop()

global_thinking_log = ThinkingLog()