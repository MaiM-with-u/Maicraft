from typing import List
import re

class ToDoItem:
    def __init__(self, details: str, reason: str, done_criteria: str):
        self.details: str = details
        self.reason: str = reason
        self.done_criteria: str = done_criteria
        self.done: bool = False

        self.id: str = ""
        
    def __str__(self):
        if self.done:
            return f"（已完成）详情：{self.details}\n{self.done_criteria}"
        return f"（未完成）详情：{self.details}\n原因：{self.reason}\n完成条件：{self.done_criteria}\n"

class ToDoList:
    def __init__(self):
        self.items: List[ToDoItem] = []
        
    def add_task(self, details: str, reason: str, done_criteria: str) -> ToDoItem:
        to_do_item = ToDoItem(details, reason, done_criteria)
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
        if not summary:
            summary = "当前没有创建或完成任何任务"
        return summary
                
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
        
        