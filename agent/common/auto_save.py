import json
import os
import threading
import time
from typing import Any, List, Dict
from utils.logger import get_logger

logger = get_logger("AutoSaveManager")

class AutoSaveManager:
    """自动保存管理器，提供通用的自动保存和加载功能"""
    
    def __init__(self, filename: str, save_interval: int = 30):
        self.filename = filename
        self.save_interval = save_interval
        self._stop_event = threading.Event()
        self._auto_save_thread = None
        self.data = None
        
    def set_data(self, data: Any):
        """设置要保存的数据"""
        self.data = data
    
    def serialize_data(self) -> Any:
        """序列化数据为可JSON保存的格式，子类可重写此方法"""
        return self.data
    
    def deserialize_data(self, loaded_data: Any) -> Any:
        """反序列化数据，子类可重写此方法"""
        return loaded_data
        
    def save_to_cache(self) -> None:
        """保存到当前目录的缓存文件"""
        try:
            serialized_data = self.serialize_data()
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump(serialized_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存到缓存失败: {e}")
    
    def save_to_data_dir(self) -> None:
        """保存到data目录"""
        data_dir = "data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        file_path = os.path.join(data_dir, self.filename)
        try:
            serialized_data = self.serialize_data()
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(serialized_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存到data目录失败: {e}")
    
    def load_from_data_dir(self) -> bool:
        """从data目录加载数据"""
        data_dir = "data"
        file_path = os.path.join(data_dir, self.filename)
        
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    loaded_data = json.load(f)
                self.data = self.deserialize_data(loaded_data)
                return True
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"读取文件失败: {e}")
                return False
        else:
            print(f"文件不存在: {file_path}")
            return False
    
    def _start_auto_save(self):
        """启动自动保存线程"""
        def auto_save_worker():
            while not self._stop_event.is_set():
                if self._stop_event.wait(self.save_interval):
                    break
                try:
                    self.save_to_data_dir()
                    logger.debug(f"{self.filename} 已自动保存")
                except Exception as e:
                    print(f"自动保存 {self.filename} 失败: {e}")
        
        self._auto_save_thread = threading.Thread(target=auto_save_worker, daemon=True)
        self._auto_save_thread.start()
    
    def start(self):
        """启动自动保存"""
        self._start_auto_save()
        
    def stop(self):
        """停止自动保存线程"""
        if self._stop_event and not self._stop_event.is_set():
            self._stop_event.set()
            if self._auto_save_thread and self._auto_save_thread.is_alive():
                self._auto_save_thread.join(timeout=2)
                print(f"{self.filename} 自动保存线程已停止")
    
    def __del__(self):
        """析构函数，确保线程被正确停止"""
        self.stop()