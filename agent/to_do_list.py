from typing import List
import re
import json
import os
from config import global_config

class MaiGoal:
    def __init__(self):
        self.goal: str = global_config.game.goal
        
mai_goal = MaiGoal()

class ToDoItem:
    def __init__(self, details: str, done_criteria: str, progress: str):
        self.details: str = details
        self.done_criteria: str = done_criteria
        self.progress: str = progress
        self.done: bool = False

        self.id: str = ""
    
    def to_dict(self):
        """转换为字典格式用于保存"""
        return {
            'details': self.details,
            'done_criteria': self.done_criteria,
            'progress': self.progress,
            'done': self.done,
            'id': self.id
        }
    
    @classmethod
    def from_dict(cls, data):
        """从字典格式创建对象"""
        item = cls(data['details'], data['done_criteria'], data['progress'])
        item.done = data['done']
        item.id = data['id']
        return item
        
    def __str__(self):
        if self.done:
            return f"（已完成）详情：{self.details}\nprogress：已完成，无需更新\n"
        return f"（未完成）详情：{self.details}\n完成条件：{self.done_criteria}\nprogress：{self.progress}\n"

class ToDoList:
    def __init__(self):
        self.items: List[ToDoItem] = []
        
        self.is_done: bool = False
        self.need_edit: str = ""
        self.data_file = "data/todo_list.json"
        # 确保data目录存在
        os.makedirs("data", exist_ok=True)
        # 启动时自动加载
        self.load_from_json()
        
    def add_task(self, details: str, done_criteria: str) -> ToDoItem:
        to_do_item = ToDoItem(details, done_criteria, "尚未开始")
        to_do_item.id = str(len(self.items)+1)
        self.items.append(to_do_item)
        # 保存到JSON文件
        self.save_to_json()
        
        return to_do_item
    
    def del_task_by_id(self, id: str):
        for item in self.items:
            if item.id == id:
                self.items.remove(item)
                # 保存到JSON文件
                self.save_to_json()
                return
            
        match = re.search(r'\d+', str(id))
        if match:
            new_id = match.group(0)
            
        for item in self.items:
            if item.id == new_id:
                self.items.remove(item)
                # 保存到JSON文件
                self.save_to_json()
                return
        
    def __str__(self):
        summary = ""
        for item in self.items:
            summary += f"task(id:{item.id})，{item}\n"
        if not summary:
            summary = "当前没有创建或完成任何任务，建议先创建一个任务"
        return summary

    
    def clear(self):
        self.items.clear()
        self.is_done = False
        # 保存到JSON文件
        self.save_to_json()
                
    def get_task_by_id(self, id: str):
        for item in self.items:
            if item.id == id:
                return item
            
            
        import re
        match = re.search(r'\d+', str(id))
        if match:
            new_id = match.group(0)
            
            for item in self.items:
                if item.id == new_id:
                    return item
            
        return None

    
    def check_if_all_done(self):
        for item in self.items:
            if not item.done:
                return False
        
        if self.need_edit:
            return False
        
        self.is_done = True
        return True
    
    def save_to_json(self) -> None:
        """保存待办事项到JSON文件"""
        data_for_save = []
        for item in self.items:
            data_for_save.append(item.to_dict())
        
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data_for_save, f, ensure_ascii=False, indent=2)
    
    def load_from_json(self) -> None:
        """从JSON文件读取待办事项"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 从字典格式创建ToDoItem对象
                self.items = []
                for item_data in data:
                    self.items.append(ToDoItem.from_dict(item_data))
            except (json.JSONDecodeError, FileNotFoundError):
                # 文件不存在或格式错误时，使用空列表
                self.items = []
    
    def update_task_progress(self, task_id: str, progress: str) -> None:
        """更新任务进度"""
        task = self.get_task_by_id(task_id)
        if task:
            task.progress = progress
            # 保存到JSON文件
            self.save_to_json()
    
    def mark_task_done(self, task_id: str) -> None:
        """标记任务为完成"""
        task = self.get_task_by_id(task_id)
        if task:
            task.done = True
            task.progress = "已完成"
            # 保存到JSON文件
            self.save_to_json()
        
mai_to_do_list = ToDoList()
mai_done_list:list[tuple[bool, str, str]] = []