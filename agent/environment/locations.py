from typing import List
from agent.environment.basic_info import BlockPosition

class LocationPoints:
    def __init__(self):
        self.location_list:List[tuple[str, str, BlockPosition]] = []
        
    def add_location(self, name: str, info: str, position: BlockPosition):
        existing_names = {location[0] for location in self.location_list}
        final_name = name
        if final_name in existing_names:
            index = 1
            while f"{name}-{index}" in existing_names:
                index += 1
            final_name = f"{name}-{index}"
        self.location_list.append((final_name, info, position))
        return final_name
        
    def remove_location(self, position: BlockPosition):
        self.location_list = [location for location in self.location_list if location[2] != position]
        
    def all_location_str(self) -> str:
        if self.location_list:
            return "\n".join([f"坐标点: [{location[0]}] {location[1]} x={location[2].x},y={location[2].y},z={location[2].z}" for location in self.location_list])
        else:
            return "未设置任何坐标点，可以在备忘录模式设置"
        
        
    def get_location(self,location_name:str) -> BlockPosition:
        for location in self.location_list:
            if location[0] == location_name:
                return location[2]
        return None
        
        
global_location_points = LocationPoints()