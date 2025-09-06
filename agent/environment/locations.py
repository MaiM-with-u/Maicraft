from typing import List
from agent.environment.basic_info import BlockPosition
from agent.common.auto_save import AutoSaveManager

class LocationPoints:
    def __init__(self):
        self.location_list:List[tuple[str, str, BlockPosition]] = []
        self.auto_save_manager = AutoSaveManager("locations.json", 30)
        self.auto_save_manager.set_data(self.location_list)
        # 启动时自动加载
        self.load_from_data_dir()
        # 启动定时保存
        self.auto_save_manager.start()
        
    def add_location(self, name: str, info: str, position: BlockPosition):
        existing_names = {location[0] for location in self.location_list}
        final_name = name
        if final_name in existing_names:
            index = 1
            while f"{name}-{index}" in existing_names:
                index += 1
            final_name = f"{name}-{index}"
        self.location_list.append((final_name, info, position))
        # 保存到data目录
        self.save_to_data_dir()
        return final_name
        
    def remove_location(self, position: BlockPosition):
        self.location_list = [location for location in self.location_list if location[2] != position]
        # 保存到data目录
        self.save_to_data_dir()
        
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
    
    def save_to_cache(self) -> None:
        """保存到当前目录的缓存文件"""
        self.auto_save_manager.save_to_cache()
    
    def save_to_data_dir(self) -> None:
        """保存坐标点到/data目录"""
        self.auto_save_manager.save_to_data_dir()
    
    def load_from_data_dir(self) -> bool:
        """从/data目录读取坐标点"""
        return self.auto_save_manager.load_from_data_dir()
    
    def stop(self):
        """停止自动保存线程"""
        self.auto_save_manager.stop()
    
    def __del__(self):
        """析构函数，确保线程被正确停止"""
        self.stop()

global_location_points = LocationPoints()