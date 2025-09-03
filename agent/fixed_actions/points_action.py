from agent.environment.basic_info import BlockPosition
from agent.environment.locations import global_location_points

async def set_location_point(name: str, info: str, position: BlockPosition):
    global_location_points.add_location(name, info, position)
    return True, f"设置坐标点: {name} {info} [{position}]"

async def remove_location_point(position: BlockPosition):
    global_location_points.remove_location(position)
    return True, f"移除坐标点: {position}"

async def get_location_point(position: BlockPosition):
    return global_location_points.get_location(position)