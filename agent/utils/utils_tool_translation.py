import json
from typing import Any
from utils.logger import get_logger
from collections import Counter

logger = get_logger("UtilsToolTranslation")

def translate_craft_item_tool_result(result: Any) -> str:
    """
    翻译craft_item工具的执行结果，使其更可读
    
    Args:
        result: craft_item工具的执行结果
        
    Returns:
        翻译后的可读文本
    """
    try:
        # 如果结果是字符串，尝试解析JSON
        if isinstance(result, str):
            try:
                result_data = json.loads(result)
            except json.JSONDecodeError:
                return str(result)
        else:
            result_data = result
        
        # 检查是否是craft_item工具的结果
        if not isinstance(result_data, dict):
            return str(result)
        
        # 提取关键信息
        ok = result_data.get("ok", False)
        data = result_data.get("data", {})
        
        if not ok:
            return "合成物品失败，可能是物品不存在或缺少工作台"
        
        # 提取合成信息
        item_name = data.get("item", "未知物品")
        count = data.get("count", 1)
        
        # 构建可读文本
        if count == 1:
            readable_text = f"成功合成1个{item_name}"
        else:
            readable_text = f"成功合成{count}个{item_name}"
        
        return readable_text
        
    except Exception:
        # 如果解析失败，返回原始结果
        return str(result)

def translate_mine_nearby_tool_result(result: Any) -> str:
    """
    翻译mine_nearby工具的执行结果，使其更可读
    """
    return translate_mine_block_tool_result(result)

def translate_mine_block_tool_result(data: Any) -> str:
    """
    翻译mine_block工具的执行结果，使其更可读
    
    Args:
        result: mine_block工具的执行结果
        
    Returns:
        翻译后的可读文本
    """
    try:
        # 如果结果是字符串，尝试解析JSON
        if isinstance(data, str):
            if "Bot does not have a harvestable tool" in data:
                return "没有合适的挖掘工具"
            return str(data)
        
        # 检查是否有挖掘数据
        if "minedCount" in data:
            # print(data)
            mined_count = data["minedCount"]
            mined_blocks = data.get("minedBlocks", [])
            
            # 统计每种方块的数量
            
            block_counts = Counter(mined_blocks)
            
            # 构建可读文本
            if len(block_counts) == 1:
                # 只有一种方块
                block_name, count = block_counts.most_common(1)[0]
                readable_text = f"成功挖掘了{count}个{block_name}"
            else:
                # 多种方块，按数量排序
                sorted_blocks = block_counts.most_common()
                block_details = "、".join([f"{count}个{name}" for name, count in sorted_blocks])
                readable_text = f"成功挖掘了{mined_count}个方块：{block_details}"
            
            return readable_text
        else:
            # 如果没有挖掘数据，返回原始结果
            return str(data)
        
    except Exception:
        # 如果解析失败，返回原始结果
        return str(data)
    
def translate_place_block_tool_result(data: str|dict) -> str:
    """
    翻译place_block工具的执行结果，使其更可读
    """

    # 如果结果是字符串，尝试解析JSON
    if isinstance(data, str):
        return str(data)
    
    block = data.get("block", "")
    position = data.get("position", {})
    referenceBlock = data.get("referenceBlock", {})
    x = position.get("x", 0)
    y = position.get("y", 0)
    z = position.get("z", 0)
    
    place_str = f"成功放置方块{block}到({x}, {y}, {z})"
    
    return place_str
        

def translate_chat_tool_result(result: Any) -> str:
    
    """
    翻译chat工具的执行结果，使其更可读
    
    Args:
        result: chat工具的执行结果
        
    Returns:
        翻译后的可读文本
    """
    try:
        # 如果结果是字符串，尝试解析JSON
        if isinstance(result, str):
            try:
                result_data = json.loads(result)
            except json.JSONDecodeError:
                return str(result)
        else:
            result_data = result
        
        # 检查是否是chat工具的结果
        if not isinstance(result_data, dict):
            return str(result)
        
        # 提取关键信息
        ok = result_data.get("ok", False)
        data = result_data.get("data", {})
        
        if not ok:
            return "聊天失败"
        
        # 提取聊天信息
        message = data.get("message", "未知消息")
        
        # 构建可读文本
        readable_text = f"成功发送消息：{message}"
        
        return readable_text
        
    except Exception:
        # 如果解析失败，返回原始结果
        return str(result)
    
def translate_view_chest_result(result: Any) -> str:
    """
    翻译view_chest工具的执行结果，使其更可读
    
    Args:
        result: view_chest工具的执行结果，来自parse_tool_result的result_content
        
    Returns:
        翻译后的可读文本
    """
    try:
        # 兼容多种输入：
        # - 字符串（完整JSON或直接data字符串）
        # - dict（完整响应或直接data对象）
        if isinstance(result, str):
            try:
                result_data = json.loads(result)
            except json.JSONDecodeError:
                return str(result)
        else:
            result_data = result

        if not isinstance(result_data, dict):
            return str(result)

        # 判断是完整响应还是已是data层
        if "block" in result_data or "containerInfo" in result_data:
            data = result_data
        else:
            ok = result_data.get("ok", True)
            if not ok:
                return "查看箱子失败，可能是箱子不存在或无法访问"
            data = result_data.get("data", {})

        # 提取箱子信息
        block = data.get("block", {})
        container_info = data.get("containerInfo", {})
        
        # 获取箱子位置
        position = block.get("position", {})
        x = position.get("x", 0)
        y = position.get("y", 0)
        z = position.get("z", 0)
        
        # 获取箱子类型和朝向
        block_name = block.get("name", "箱子")
        properties = block.get("_properties", {})
        facing = properties.get("facing", "未知")
        
        # 获取容器统计信息
        stats = container_info.get("stats", {})
        total_slots = stats.get("totalSlots", 0)
        occupied_slots = stats.get("occupiedSlots", 0)
        empty_slots = stats.get("emptySlots", 0)
        occupancy_rate = stats.get("occupancyRate", "0%")
        
        # 获取物品列表
        slots = container_info.get("slots", [])
        items = []
        
        for slot in slots:
            # logger.info(f"箱子物品: {slot}")
            if slot.get("name") != "air" and slot.get("count", 0) > 0:
                item_name = slot.get("name", "未知物品")
                count = slot.get("count", 1)
                
                items.append(f"{item_name} x {count}")
        
        # 构建可读文本
        readable_text = "箱子chest({x}, {y}, {z})的内容：\n"
        readable_text += f"容量: {total_slots}格，已占用: {occupied_slots}格，空闲: {empty_slots}格 ({occupancy_rate})\n"
        
        if items:
            readable_text += "物品列表:\n"
            for item in items:
                readable_text += f"  {item}\n"
        else:
            readable_text += "箱子为空"
        
        return readable_text
        
    except Exception:
        # 如果解析失败，返回原始结果
        return str(result)



def translate_view_furnace_result(result: Any) -> str:
    """翻译view_furnace工具的执行结果"""
    try:
        # 兼容字符串或字典输入
        if isinstance(result, str):
            try:
                result_data = json.loads(result)
            except json.JSONDecodeError:
                return str(result)
        else:
            result_data = result

        if not isinstance(result_data, dict):
            return str(result)

        # 判断层级
        if "block" in result_data or "containerInfo" in result_data:
            data = result_data
        else:
            ok = result_data.get("ok", True)
            if not ok:
                return "查看熔炉失败"
            data = result_data.get("data", {})

        block = data.get("block", {})
        container_info = data.get("containerInfo", {})
        
        # 获取熔炉位置
        position = block.get("position", {})
        x, y, z = position.get("x", 0), position.get("y", 0), position.get("z", 0)
        
        # 获取熔炉状态
        properties = block.get("_properties", {})
        lit = properties.get("lit", False)
        
        # 获取熔炉专用信息
        furnace_info = container_info.get("furnaceInfo", {})
        fuel = furnace_info.get("fuel", 0)
        progress = furnace_info.get("progress", 0)
        
        # 获取物品列表并映射槽位
        slots = container_info.get("slots", [])
        slot_names = {0: "input", 1: "fuel", 2: "output"}
        
        readable_text = f"✅ 熔炉 ({x}, {y}, {z})\n"
        readable_text += f"状态: {'🔥 燃烧中' if lit else '❄️ 未燃烧'}\n"
        
        if fuel > 0:
            readable_text += f"燃料: {fuel}%\n"
        if progress > 0:
            readable_text += f"进度: {progress}%\n"
        
        if slots:
            for slot in slots:
                if slot.get("name") != "air" and slot.get("count", 0) > 0:
                    slot_num = slot.get("slot", 0)
                    slot_name = slot_names.get(slot_num, f"槽位{slot_num}")
                    item_name = slot.get("name", "未知")
                    count = slot.get("count", 1)
                    readable_text += f"{slot_name}: {count}个{item_name}\n"
        else:
            readable_text += "熔炉为空"
        
        return readable_text
        
    except Exception:
        return str(result)

def translate_use_chest_tool_result(data: Any) -> str:
    """
    翻译use_chest工具的执行结果，使其更可读
    
    Args:
        result: use_chest工具的执行结果
        
    Returns:
        翻译后的可读文本
    """
    try:
        # 如果结果是字符串，尝试解析JSON
        if isinstance(data, str):
            return str(data)
        
        # 提取操作结果信息
        operation_results = data.get("operationResults", [])
        chest_contents = data.get("chestContents", [])
        chest_location = data.get("chestLocation", {})
        
        # 构建可读文本
        readable_text = ""
        
        # 添加操作结果
        if operation_results:
            for operation in operation_results:
                readable_text += f"{operation};"
        
        # 添加箱子位置信息
        if chest_location:
            x = chest_location.get("x", 0)
            y = chest_location.get("y", 0)
            z = chest_location.get("z", 0)
            readable_text += f"箱子位置: ({x}, {y}, {z})\n"
        
        # 添加箱子内容信息
        # if chest_contents:
        #     readable_text += "箱子内容:\n"
        #     for item in chest_contents:
        #         item_name = item.get("name", "未知物品")
        #         count = item.get("count", 1)
        #         if count == 1:
        #             readable_text += f"  {item_name}: 1个\n"
        #         else:
        #             readable_text += f"  {item_name}: {count}个\n"
        # else:
        #     readable_text += "箱子为空\n"
        
        return readable_text
        
    except Exception:
        # 如果解析失败，返回原始结果
        return str(data)

def translate_use_furnace_tool_result(data: Any) -> str:
    """翻译use_furnace工具的执行结果"""
    try:
        if isinstance(data, str):
            return str(data)

        operation_results = data.get("operationResults", [])
        container_contents = data.get("containerContents", [])
        
        # 槽位映射
        slot_names = {0: "input", 1: "fuel", 2: "output"}
        
        readable_text = ""
        
        if operation_results:
            readable_text += f"{operation_results[0]}\n"
        
        if container_contents:
            for item in container_contents:
                slot = item.get("slot", 0)
                slot_name = slot_names.get(slot, f"槽位{slot}")
                item_name = item.get("name", "未知")
                count = item.get("count", 1)
                readable_text += f"{slot_name}: {count}个{item_name}\n"
        
        return readable_text
        
    except Exception:
        return str(data)