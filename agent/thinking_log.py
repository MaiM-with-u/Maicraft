import json
class ThinkingLog:
    """思考记录"""
    def __init__(self):
        self.thinking_list = []
        
    def add_thinking_log(self, thinking_log: str) -> None:
        self.thinking_list.append(thinking_log)
        if len(self.thinking_list) > 20:
            self.thinking_list = self.thinking_list[-20:]
        
    def get_thinking_log(self) -> str:
        return "\n".join(self.thinking_list)
    
    def save_to_cache(self) -> None:
        with open("thinking_log.json", "w") as f:
            json.dump(self.thinking_list, f)
    
global_thinking_log = ThinkingLog()