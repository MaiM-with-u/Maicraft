from typing import Dict, Any, List
from agent.environment.basic_info import Item

def review_all_tools(inventory:List[Item]) -> str:
    pickaxe_tip_str = review_pickaxe(inventory)
    axe_tip_str = review_axe(inventory)
    shovel_tip_str = review_shovel(inventory)
    hoe_tip_str = review_hoe(inventory)
    sword_tip_str = review_sword(inventory)
    return f"{pickaxe_tip_str}{axe_tip_str}{shovel_tip_str}{hoe_tip_str}{sword_tip_str}"

def review_pickaxe(inventory:List[Item]) -> str:
    max_tool_material = ""
    max_tool_material_level = 0
    tool_list:List[Item] = []
    for item in inventory:
        if item.tool_type == "pickaxe":
            tool_list.append(item)
            if item.tool_material_level > max_tool_material_level:
                max_tool_material_level = item.tool_material_level
                max_tool_material = item.tool_material
        
    tool_tip_str = ""
    if len(tool_list) == 0:
        tool_tip_str = "背包中没有任何稿子，挖掘石质方块和矿物将会很困难，需要合成\n"
    elif len(tool_list) == 1:
        if max_tool_material_level == 1:
            tool_tip_str = "背包中只有一把木质稿子，只能挖掘石头和煤矿，无法开采更高级的矿物，需要合成更高级的稿子。\n"
        elif max_tool_material_level == 2:
            tool_tip_str = "背包中只有一把金质稿子，只能挖掘石头和煤矿，无法开采更高级的矿物，需要合成更高级的稿子。\n"
        elif max_tool_material_level == 3:
            tool_tip_str = "背包中只有一把石质稿子，能够挖掘铁矿以及更低级的矿物，无法开采更高级的矿物，需要合成更高级的稿子。如果需要挖矿或建造，可以多携带几把稿子。\n"
        elif max_tool_material_level == 4:
            tool_tip_str = "背包中只有一把铁质稿子，能够开采石头至钻石块的所有矿物。如果需要挖矿或建造，可以多携带几把稿子。\n"
        elif max_tool_material_level == 5:
            tool_tip_str = "背包中有一把钻石稿子，能够开采石头至下界合金块的所有矿物，挖掘速度很快。如果需要挖矿或建造，可以多携带几把稿子。\n"
        elif max_tool_material_level == 6:
            tool_tip_str = "背包中有一把下界合金稿子，能够开采所有石质方块\n"
    elif len(tool_list) > 1:
        all_pickaxe_str = ""
        for item in tool_list:
            all_pickaxe_str += f"{item.tool_material}稿子, "
        all_pickaxe_str = f"背包中有:[{all_pickaxe_str}]"
        
        if max_tool_material_level == 1:
            tool_tip_str = f"{all_pickaxe_str}，最高等级为木质稿子，能够挖掘石头和煤矿，无法开采更高级的矿物，需要合成更高级的稿子\n"
        elif max_tool_material_level == 2:
            tool_tip_str = f"{all_pickaxe_str}，最高等级为金质稿子，能够挖掘石头和煤矿，无法开采更高级的矿物，需要合成更高级的稿子\n"
        elif max_tool_material_level == 3:
            tool_tip_str = f"{all_pickaxe_str}，最高等级为石质稿子，能够挖掘铁矿以及更低级的矿物，无法开采更高级的矿物，需要合成更高级的稿子\n"
        elif max_tool_material_level == 4:
            tool_tip_str = f"{all_pickaxe_str}，最高等级为铁质稿子，能够开采石头至钻石块的所有矿物\n"
        elif max_tool_material_level == 5:
            tool_tip_str = f"{all_pickaxe_str}，最高等级为钻石稿子，能够开采石头至下界合金块的所有矿物，挖掘速度很快\n"
        elif max_tool_material_level == 6:
            tool_tip_str = f"{all_pickaxe_str}，最高等级为下界合金稿子，能够开采所有石质方块\n"
    return tool_tip_str
        
def review_axe(inventory:List[Item]) -> str:
    max_tool_material = ""
    max_tool_material_level = 0
    tool_list:List[Item] = []
    for item in inventory:
        if item.tool_type == "axe":
            tool_list.append(item)
            if item.tool_material_level > max_tool_material_level:
                max_tool_material_level = item.tool_material_level
                max_tool_material = item.tool_material
        
    tool_tip_str = ""
    if len(tool_list) == 0:
        tool_tip_str = "背包中没有任何斧子，砍树或挖掘木制方块将会很困难，需要合成\n"
    elif len(tool_list) == 1:
        if max_tool_material_level == 1:
            tool_tip_str = "背包中只有一把木质斧子，但是耐久度低，需要尽快升级\n"
        elif max_tool_material_level == 2:
            tool_tip_str = "背包中只有一把金质斧子，但是耐久度低，需要尽快升级\n"
        elif max_tool_material_level == 3:
            tool_tip_str = "背包中只有一把石质斧子，挖掘速度一般，如果有富余的材料，可以合成更高级的斧子\n"
        elif max_tool_material_level == 4:
            tool_tip_str = "背包中只有一把铁质斧子，如果有非常富余的材料，可以合成更高级的斧子\n"
        elif max_tool_material_level == 5:
            tool_tip_str = "背包中只有一把钻石斧子，可以快速采集所有木质方块。\n"
        elif max_tool_material_level == 6:
            tool_tip_str = "背包中只有一把下界合金斧子，可以极快速采集所有木质方块。\n"
    elif len(tool_list) > 1:
        all_axe_str = ""
        for item in tool_list:
            all_axe_str += f"{item.tool_material}斧子, "
        all_axe_str = f"背包中有:[{all_axe_str}]"
        
        if max_tool_material_level == 1:
            tool_tip_str = f"{all_axe_str}，最高等级为木质斧子，但是耐久度低，需要尽快升级\n"
        elif max_tool_material_level == 2:
            tool_tip_str = f"{all_axe_str}，最高等级为金质斧子，但是耐久度低，需要尽快升级\n"
        elif max_tool_material_level == 3:
            tool_tip_str = f"{all_axe_str}，最高等级为石质斧子，挖掘速度一般，如果有富余的材料，可以合成更高级的斧子\n"
        elif max_tool_material_level == 4:
            tool_tip_str = f"{all_axe_str}，最高等级为铁质斧子，如果有非常富余的材料，可以合成更高级的斧子\n"
        elif max_tool_material_level == 5:
            tool_tip_str = f"{all_axe_str}，最高等级为钻石斧子，可以快速采集所有木质方块。\n"
        elif max_tool_material_level == 6:
            tool_tip_str = f"{all_axe_str}，最高等级为下界合金斧子，可以极快速采集所有木质方块。\n"
        
    return tool_tip_str

def review_shovel(inventory:List[Item]) -> str:
    max_tool_material = ""
    max_tool_material_level = 0
    tool_list:List[Item] = []
    for item in inventory:
        if item.tool_type == "shovel":
            tool_list.append(item)
            if item.tool_material_level > max_tool_material_level:
                max_tool_material_level = item.tool_material_level
                max_tool_material = item.tool_material
                
    tool_tip_str = ""
    if len(tool_list) == 0:
        tool_tip_str = "背包中没有任何shovel，挖掘泥土，沙子或砂砾等方块效率较低，需要合成shovel\n"
    elif len(tool_list) == 1:
        if max_tool_material_level == 1:
            tool_tip_str = "背包中有一把木质铲子，耐久度极低，需要尽快升级\n"
        elif max_tool_material_level == 2:
            tool_tip_str = "背包中有一把金质铲子，耐久度极低，需要尽快升级\n"
        elif max_tool_material_level == 3:
            tool_tip_str = "背包中有一把石质铲子，挖掘速度一般，如果有富余的材料，可以合成更高级的铲子\n"
        elif max_tool_material_level == 4:
            tool_tip_str = "背包中有一把铁质铲子，如果有非常富余的材料，可以合成更高级的铲子\n"
        elif max_tool_material_level == 5:
            tool_tip_str = "背包中有一把钻石铲子，可以快速挖掘泥土，沙子或砂砾等方块\n"
        elif max_tool_material_level == 6:
            tool_tip_str = "背包中有一把下界合金铲子，可以极快速挖掘泥土，沙子或砂砾等方块\n"
    elif len(tool_list) > 1:
        all_shovel_str = ""
        for item in tool_list:
            all_shovel_str += f"{item.tool_material}铲子, "
        all_shovel_str = f"背包中有:[{all_shovel_str}]"
        
        if max_tool_material_level == 1:
            tool_tip_str = f"{all_shovel_str}，最高等级为木质铲子，耐久度极低，需要尽快升级\n"
        elif max_tool_material_level == 2:
            tool_tip_str = f"{all_shovel_str}，最高等级为金质铲子，耐久度极低，需要尽快升级\n"
        elif max_tool_material_level == 3:
            tool_tip_str = f"{all_shovel_str}，最高等级为石质铲子，挖掘速度一般，如果有富余的材料，可以合成更高级的铲子\n"
        elif max_tool_material_level == 4:
            tool_tip_str = f"{all_shovel_str}，最高等级为铁质铲子，如果有非常富余的材料，可以合成更高级的铲子\n"
        elif max_tool_material_level == 5:
            tool_tip_str = f"{all_shovel_str}，最高等级为钻石铲子，可以快速挖掘泥土，沙子或砂砾等方块\n"
        elif max_tool_material_level == 6:
            tool_tip_str = f"{all_shovel_str}，最高等级为下界合金铲子，可以极快速挖掘泥土，沙子或砂砾等方块\n"
        

    return tool_tip_str


def review_hoe(inventory:List[Item]) -> str:
    max_tool_material = ""
    max_tool_material_level = 0
    tool_list:List[Item] = []
    for item in inventory:
        if item.tool_type == "hoe":
            tool_list.append(item)
            if item.tool_material_level > max_tool_material_level:
                max_tool_material_level = item.tool_material_level
                max_tool_material = item.tool_material
                
    tool_tip_str = ""
    if len(tool_list) == 0:
        tool_tip_str = "背包中没有锄头，如果想要farm，可以合成锄头\n"
    elif len(tool_list) > 1:
        all_hoe_str = ""
        for item in tool_list:
            all_hoe_str += f"{item.tool_material}锄头, "
        all_hoe_str = f"背包中有:[{all_hoe_str}]，如果不需要进行farm，不要携带这么多锄头\n"
        tool_tip_str = all_hoe_str
    
    return tool_tip_str
    
def review_sword(inventory:List[Item]) -> str:
    max_tool_material = ""
    max_tool_material_level = 0
    tool_list:List[Item] = []
    for item in inventory:
        if item.tool_type == "sword":
            tool_list.append(item)
            if item.tool_material_level > max_tool_material_level:
                max_tool_material_level = item.tool_material_level
                max_tool_material = item.tool_material
                
    tool_tip_str = ""
    if len(tool_list) == 0:
        tool_tip_str = "背包中没有任何剑，攻击效率较低，需要合成剑\n"
    elif len(tool_list) == 1:
        if max_tool_material_level == 1:
            tool_tip_str = "背包中有一把木质剑，耐久度极低，攻击力加成低，需要尽快升级\n"
        elif max_tool_material_level == 2:
            tool_tip_str = "背包中有一把金质剑，耐久度极低，攻击力加成低，需要尽快升级\n"
        elif max_tool_material_level == 3:
            tool_tip_str = "背包中有一把石质剑，攻击力加成一般，如果有富余的材料，可以合成更高级的剑\n"
        elif max_tool_material_level == 4:
            tool_tip_str = "背包中有一把铁质剑，如果有非常富余的材料，可以合成更高级的剑\n"
        elif max_tool_material_level == 5:
            tool_tip_str = "背包中有一把钻石剑，可以快速击杀怪物\n"
            
    elif len(tool_list) > 1:
        all_sword_str = ""
        for item in tool_list:
            all_sword_str += f"{item.tool_material}剑, "
        all_sword_str = f"背包中有:[{all_sword_str}]，携带太多剑容易浪费背包空间，建议携带一把\n"
        
        if max_tool_material_level == 1:
            tool_tip_str = f"{all_sword_str}，最高等级为木质剑，耐久度极低，攻击力加成低，需要尽快升级\n"
        elif max_tool_material_level == 2:
            tool_tip_str = f"{all_sword_str}，最高等级为金质剑，耐久度极低，攻击力加成低，需要尽快升级\n"
        elif max_tool_material_level == 3:
            tool_tip_str = f"{all_sword_str}，最高等级为石质剑，攻击力加成一般，如果有富余的材料，可以合成更高级的剑\n"
        elif max_tool_material_level == 4:
            tool_tip_str = f"{all_sword_str}，最高等级为铁质剑，如果有非常富余的材料，可以合成更高级的剑\n"
        elif max_tool_material_level == 5:
            tool_tip_str = f"{all_sword_str}，最高等级为钻石剑，可以快速击杀怪物\n"
            
    return tool_tip_str


def get_held_item_info(held_item: Dict[str, Any]) -> str:
    """获取手持物品的详细信息"""
    if not held_item:
        return "没有手持物品"
    
    item_name = held_item.get("displayName", held_item.get("name", "未知物品"))
    item_count = held_item.get("count", 1)
    durability = held_item.get("maxDurability", 0)
    
    info_lines = [f"手持物品: {item_name} x{item_count}"]
    
    # 添加耐久度信息
    if durability > 1:
        current_damage = 0
        if held_item.get("components"):
            for component in held_item["components"]:
                if component.get("type") == "damage":
                    current_damage = component.get("data", 0)
                    break
        
        remaining_durability = durability - current_damage
        info_lines.append(f"耐久度: {remaining_durability}/{durability}")
        
        # 添加耐久度百分比
        if durability > 0:
            durability_percent = (remaining_durability / durability) * 100
            info_lines.append(f"耐久度百分比: {durability_percent:.1f}%")
    
    # 添加物品类型信息
    if held_item.get("material"):
        info_lines.append(f"挖掘工具: {held_item['material']}")
    
    return "\n".join(info_lines)
