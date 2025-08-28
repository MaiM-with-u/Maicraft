

class ModelConfig:
    def __init__(self,model_name:str,api_key:str,base_url:str,max_tokens:int,temperature:float):
        self.model_name:str = model_name
        self.api_key:str = api_key
        self.base_url:str = base_url
        self.max_tokens:int = max_tokens
        self.temperature:float = temperature