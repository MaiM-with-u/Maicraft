from agent.environment.environment import global_environment
from agent.smart_craft.craft_action import recipe_finder
from agent.smart_craft.craft_action import Item

async def craft_item(item, count) -> tuple[bool,str]:
    result_str = f"想要合成: {item} 数量: {count}\n"
    
    ok, summary = await recipe_finder.craft_item_smart(item, count, global_environment.inventory, global_environment.block_position)
    if ok:
        result_str = f"合成成功：{item} x{count}\n{summary}\n"
        is_success = True
    else:
        result_str = f"合成未完成：{item} x{count}\n{summary}\n"
        is_success = False
        
    return is_success,result_str