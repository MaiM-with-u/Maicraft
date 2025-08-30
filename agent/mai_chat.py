from typing import List

class MinecraftMessage:
    def __init__(self, message:str, sender:str, type:str, timestamp:str):
        self.message = message
        self.sender = sender
        self.type = type
        self.timestamp = timestamp

class ChatManager:
    def __init__(self):
        self.message_history:List[MinecraftMessage] = []
    
    def add_message(self, message:str, sender:str, type:str, timestamp:str):
        self.message_history.append(MinecraftMessage(message, sender, type, timestamp))
    
    def get_message_history(self):
        return self.message_history
    
    