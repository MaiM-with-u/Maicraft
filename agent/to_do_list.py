from typing import List
import re

class ToDoItem:
    def __init__(self, details: str, done_criteria: str, progress: str):
        self.details: str = details
        self.done_criteria: str = done_criteria
        self.progress: str = progress
        self.done: bool = False

        self.id: str = ""
        
    def __str__(self):
        if self.done:
            return f"（已完成）详情：{self.details}\nprogress：已完成，无需更新\n"
        return f"（未完成）详情：{self.details}\n完成条件：{self.done_criteria}\nprogress：{self.progress}\n"

class ToDoList:
    def __init__(self):
        self.items: List[ToDoItem] = []
        
        self.is_done: bool = False
        self.need_edit: str = ""
        
    def add_task(self, details: str, done_criteria: str) -> ToDoItem:
        to_do_item = ToDoItem(details, done_criteria, "尚未开始")
        to_do_item.id = str(len(self.items)+1)
        self.items.append(to_do_item)
        
        return to_do_item
    
    def del_task_by_id(self, id: str):
        for item in self.items:
            if item.id == id:
                self.items.remove(item)
                return
            
        match = re.search(r'\d+', str(id))
        if match:
            new_id = match.group(0)
            
        for item in self.items:
            if item.id == new_id:
                self.items.remove(item)
                return
        
    def __str__(self):
        summary = ""
        for item in self.items:
            summary += f"task(id:{item.id})，{item}\n"
        return summary

    
    def clear(self):
        self.items.clear()
        self.is_done = False
                
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
        
        