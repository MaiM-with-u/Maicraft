from agent.environment.basic_info import BlockPosition

class Basement:
    """游戏基地坐标"""
    def __init__(self):
        self.set = False
        self.position:BlockPosition = None
        self.basement_info = []
        
    def distance_from_player(self, player_position: BlockPosition) -> float:
        if self.set:
            return self.position.distance(player_position)
        return 0
    
    def add_basement_info(self, info: str, position: BlockPosition):
        self.position = position
        self.basement_info.append(info)
        self.set = True
    
    def get_basement_info(self) -> str:
        return "\n".join(self.basement_info)
    
global_basement = Basement()
        
        