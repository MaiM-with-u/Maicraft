import asyncio
import time
from agent.block_cache.block_cache import global_block_cache
from agent.block_cache.nearby_block import nearby_block_manager
from agent.environment.environment import global_environment
from agent.utils.utils import (
    parse_tool_result,
)
from agent.utils.utils_tool_translation import (
    translate_mine_nearby_tool_result, 
    translate_mine_block_tool_result, 
)
from utils.logger import get_logger
from mcp_server.client import global_mcp_client
logger = get_logger("mine_action")


def translate_result(result: str) -> str:
    if "不可见" in result:
        return "挖掘失败！视野内没有{name}方块\n"
    elif "harvestable" in result:
        return "没有合适的挖掘工具，稿子等级不足，需要合成合适的稿子，请查看物品栏"
    elif "safe" in result:
        return "要挖掘位置不安全，附近有水或者可能导致沙子砂砾塌方，请挖掘其他地方"
    else:
        return f"批量挖掘失败: {result}"
    
async def mine_nearby_blocks(name: str, count: int,digOnly:bool) -> tuple[bool,str]:
    result_str = ""
    args = {"name": name, "count": count,"digOnly": digOnly,"enable_xray":True}
    call_result = await global_mcp_client.call_tool_directly("mine_block", args)
    is_success, result_content = parse_tool_result(call_result)
    if is_success:
        result_str += translate_mine_nearby_tool_result(result_content)
    else:
        result_str += translate_result(result_content)
        
    return is_success,result_str
    
async def mine_block_by_position(x,y,z,digOnly: bool) -> tuple[bool,str]:
    """
    挖掘某个位置的方块
    x,y,z是方块的坐标
    digOnly是是否只挖掘，如果为True，则不收集方块
    return tuple[bool,str,bool]，bool为是否成功，bool为位置是否存在方块或方块是否可以挖掘
    """
    result_str = f""
    block_cache = global_block_cache.get_block(x, y, z)
    if not block_cache:
        # result_str += f"位置{x},{y},{z}不存在方块，无法挖掘\n"
        return False,result_str
    if block_cache.block_type == "air" or block_cache.block_type == "cave_air":
        # result_str += f"位置{x},{y},{z}不存在方块，无法挖掘\n"
        return False,result_str
    if block_cache.block_type == "water" or block_cache.block_type == "lava" or block_cache.block_type == "bedrock":
        result_str += f"位置{x},{y},{z}是{block_cache.block_type}，无法挖掘\n"
        return False,result_str
    
    args = {"x": x, "y": y, "z": z, "digOnly": digOnly,"enable_xray":True}
    call_result = await global_mcp_client.call_tool_directly("mine_block", args)
    is_success, result_content = parse_tool_result(call_result)
    if is_success:
        result_str += translate_mine_block_tool_result(result_content)
    else:
        result_str += translate_result(result_content)
    
    return is_success,result_str

async def mine_in_direction(direction: str, timeout: float, digOnly: bool) -> tuple[bool, str]:
    """
    按方向持续挖掘，直到超时或挖掘失败
    direction: 方向 (+x, -x, +y, -y, +z, -z)
    timeout: 超时时间（秒）
    digOnly: 是否只挖掘，不收集方块
    """
    result_str = ""
    start_time = time.time()
    blocks_mined = 0
    
    # 解析方向
    if direction == "+x":
        dx, dy, dz = 1, 0, 0
    elif direction == "-x":
        dx, dy, dz = -1, 0, 0
    elif direction == "+y":
        dx, dy, dz = 0, 1, 0
    elif direction == "-y":
        dx, dy, dz = 0, -1, 0
    elif direction == "+z":
        dx, dy, dz = 0, 0, 1
    elif direction == "-z":
        dx, dy, dz = 0, 0, -1
    else:
        return False, f"不支持的方向: {direction}，请使用 +-x, +-y, +-z"
    
    result_str += f"开始向{direction}方向挖掘，超时时间：{timeout}秒\n"
    
    # 记录起始位置
    try:
        start_pos = global_environment.block_position
        
        if not start_pos:
            return False, "无法获取玩家位置"
        
        # 确保start_pos是BlockPosition对象
        if not hasattr(start_pos, 'x'):
            # 如果不是BlockPosition对象，可能是整数或其他类型
            try:
                # 尝试从global_environment.position获取
                current_pos = global_environment.position
                
                if current_pos and hasattr(current_pos, 'x'):
                    from agent.common.basic_class import BlockPosition
                    start_pos = BlockPosition(current_pos)
                else:
                    return False, "无法获取有效的玩家位置"
            except Exception as e:
                return False, f"无法创建位置对象: {str(e)}"
        
        # 计算当前挖掘距离
        current_distance = 0
        
    except Exception as e:
        return False, f"获取起始位置失败: {str(e)}"
    
    mine_timeout = timeout
    
    while time.time() - start_time < mine_timeout:
        # 获取当前位置
        try:
            await asyncio.sleep(0.2)
            current_pos = global_environment.block_position
            
            if not current_pos:
                return False, "无法获取玩家位置"
            
            # 从起始位置计算目标位置
            
            if hasattr(start_pos, 'x') and hasattr(start_pos, 'y') and hasattr(start_pos, 'z'):
                target_x = int(start_pos.x + dx * (2 + current_distance))
                target_y = int(start_pos.y + dy * (2 + current_distance))
                target_z = int(start_pos.z + dz * (2 + current_distance))
            else:
                break
            
            # 检查目标位置的方块
            block_cache = global_block_cache.get_block(target_x, target_y, target_z)
            if not block_cache:
                result_str += f"位置{target_x},{target_y},{target_z}不存在方块，停止挖掘\n"
                break
            
            if block_cache.block_type in ["air", "cave_air"]:
                # 检查上方一格是否也是空气
                upper_block_cache = global_block_cache.get_block(target_x, target_y + 1, target_z)
                if upper_block_cache and upper_block_cache.block_type in ["air", "cave_air"]:
                    # 两格都是空气，增加挖掘距离
                    current_distance += 1
                    result_str += f"位置{target_x},{target_y},{target_z}和{target_x},{target_y+1},{target_z}都是空方块，增加挖掘距离\n"
                    await asyncio.sleep(0.2)
                    continue
                else:
                    result_str += f"位置{target_x},{target_y},{target_z}是空方块但上方不是，准备挖掘\n"
            
            if block_cache.block_type in ["water", "lava", "bedrock"]:
                result_str += f"遇到{block_cache.block_type}，停止挖掘\n"
                break
            
            # 检查周围可见的矿石方块
            ore_collect_start = time.time()
            
            ore_result = await _check_and_mine_nearby_ores(current_pos)
            result_str += ore_result
            
            ores_collect_end = time.time()
            ores_collect_time = ores_collect_end - ore_collect_start
            mine_timeout += ores_collect_time
            
            # 挖掘两格高的隧道
            all_success = True
            for height_offset in [0, 1]:
                await asyncio.sleep(0.2)
                mine_y = target_y + height_offset
                
                # 检查这个高度的方块
                upper_block_cache = global_block_cache.get_block(target_x, mine_y, target_z)
                if not upper_block_cache or upper_block_cache.block_type in ["air", "cave_air"]:
                    result_str += f"位置{target_x},{mine_y},{target_z}不存在方块，跳过\n"
                    continue
                
                if upper_block_cache.block_type in ["water", "lava", "bedrock"]:
                    result_str += f"遇到{upper_block_cache.block_type}，停止挖掘\n"
                    all_success = False
                    break
                
                type = upper_block_cache.block_type
                
                # 挖掘方块
                args = {"x": target_x, "y": mine_y, "z": target_z, "digOnly": digOnly, "enable_xray": True}
                call_result = await global_mcp_client.call_tool_directly("mine_block", args)
                is_success, result_content = parse_tool_result(call_result)
                
                if is_success:
                    if type not in ["air", "cave_air"]:
                        blocks_mined += 1
                        result_str += f"成功挖掘{target_x},{mine_y},{target_z}的{type}\n"
                    else:
                        result_str += f"跳过{target_x},{mine_y},{target_z}的空气方块\n"
                else:
                    result_str += translate_result(result_content)
                    all_success = False
                    break
            
            # 只有当两格都挖掘成功后才增加挖掘距离
            if all_success:
                current_distance += 1
            else:
                break
            
            # 短暂延迟避免过快操作
            await asyncio.sleep(0.5)
            
        except Exception as e:
            import traceback
            result_str += f"挖掘过程中出现错误: {str(e)}\n"
            result_str += f"Traceback: {traceback.format_exc()}\n"
            break
    
    result_str += f"挖掘结束，共挖掘{blocks_mined}个方块\n"
    return True, result_str

async def _check_and_mine_nearby_ores(current_pos):
    """检查周围可见的矿石方块并进行批量挖掘"""
    from agent.common.basic_class import BlockPosition
    
    result_str = ""
    
    # 确保current_pos是BlockPosition对象
    if not hasattr(current_pos, 'x'):
        result_str += f"DEBUG: current_pos没有x属性\n"
        # 如果不是BlockPosition对象，尝试从global_environment.position获取
        try:
            env_pos = global_environment.position
            if env_pos and hasattr(env_pos, 'x'):
                current_pos = BlockPosition(env_pos)
            else:
                return "无法获取有效的玩家位置来检查矿石"
        except Exception as e:
            return f"创建位置对象失败: {str(e)}"
    
    # 获取当前位置周围的可见方块
    mine_failed = False
    while not mine_failed:
        await asyncio.sleep(0.3)
        pos = BlockPosition(x=current_pos.x, y=current_pos.y, z=current_pos.z)
        visible_blocks = await nearby_block_manager.get_visible_blocks_list(pos, distance=16)
        
        # 找出所有矿石方块
        ore_blocks = {}
        has_ore = False
        # logger.info(f"发现周围矿石：{visible_blocks}")
        for block in visible_blocks:
            if "ore" in block["type"].lower():
                ore_type = block["type"]
                if ore_type not in ore_blocks:
                    ore_blocks[ore_type] = []
                ore_blocks[ore_type].append((block["x"], block["y"], block["z"]))
                has_ore = True
        if not has_ore:
            break
        
        # 如果有矿石方块，进行批量挖掘
        if ore_blocks:
            logger.info(f"发现周围矿石：{', '.join(ore_blocks.keys())}，开始批量挖掘...\n")
            result_str += f"发现周围矿石：{', '.join(ore_blocks.keys())}，开始批量挖掘...\n"
            for ore_type, positions in ore_blocks.items():
                result_str += f"挖掘{ore_type}，共{len(positions)}个\n"
                ore_success, ore_result = await mine_nearby_blocks(ore_type, len(positions), digOnly=False)
                logger.info(f"挖掘{ore_type}，共{len(positions)}个，结果：{ore_result}")
                result_str += ore_result
                if ore_success:
                    logger.info(f"{ore_type}挖掘完成")
                    # result_str += f"{ore_type}挖掘完成\n"
                else:
                    logger.info(f"{ore_type}挖掘失败")
                    # result_str += f"{ore_type}挖掘失败\n"
                    mine_failed = True
                    break
                    
                    
    return result_str

async def mine_block(type:str,x:int,y:int,z:int,name:str,count:int,digOnly:bool,direction:str="",timeout:float=0) -> tuple[bool,str]:
    if type == "nearby":
        return await mine_nearby_blocks(name, count,digOnly=digOnly)
    elif type == "position":
        return await mine_block_by_position(x, y, z, digOnly=digOnly)
    elif type == "direction":
        return await mine_in_direction(direction, timeout, digOnly)
    else:
        return False,f"不支持的挖掘类型: {type}，请使用nearby、position或direction"
