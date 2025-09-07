import json
import os
from typing import List
from agent.common.basic_class import BlockPosition

class LocationPoints:
    def __init__(self):
        self.location_list:List[tuple[str, str, BlockPosition]] = []
        self.data_file = "data/locations.json"
        # 确保data目录存在
        os.makedirs("data", exist_ok=True)
        # 加载数据
        self.load_from_json()
        
    def add_location(self, name: str, info: str, position: BlockPosition):
        existing_names = {location[0] for location in self.location_list}
        final_name = name
        if final_name in existing_names:
            index = 1
            while f"{name}-{index}" in existing_names:
                index += 1
            final_name = f"{name}-{index}"
        self.location_list.append((final_name, info, position))
        # 保存到JSON文件
        self.save_to_json()
        return final_name
        
    def remove_location(self, position: BlockPosition):
        self.location_list = [location for location in self.location_list if location[2] != position]
        # 保存到JSON文件
        self.save_to_json()
        
    def all_location_str(self) -> str:
        if self.location_list:
            return "\n".join([f"坐标点: [{location[0]}] {location[1]} x={location[2].x},y={location[2].y},z={location[2].z}" for location in self.location_list])
        else:
            return "未设置任何坐标点，可以进行设置"
        
        
    def get_location(self,location_name:str) -> BlockPosition:
        for location in self.location_list:
            if location[0] == location_name:
                return location[2]
        return None
    
    def save_to_json(self) -> None:
        """保存坐标点到JSON文件"""
        # 将 BlockPosition 对象转换为字典格式
        data_for_save = []
        for name, info, position in self.location_list:
            if isinstance(position, BlockPosition):
                position_dict = position.to_dict()
            else:
                position_dict = position
            data_for_save.append((name, info, position_dict))
        
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data_for_save, f, ensure_ascii=False, indent=2)
    
    def load_from_json(self) -> None:
        """从JSON文件读取坐标点"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 将字典格式的数据转换为 BlockPosition 对象
                converted_data = []
                for item in data:
                    if len(item) == 3:
                        name, info, position_data = item
                        if isinstance(position_data, dict):
                            # 如果是字典格式，转换为 BlockPosition 对象
                            position = BlockPosition(position_data)
                        else:
                            position = position_data
                        converted_data.append((name, info, position))
                self.location_list = converted_data
            except (json.JSONDecodeError, FileNotFoundError):
                # 文件不存在或格式错误时，使用空列表
                self.location_list = []

global_location_points = LocationPoints()