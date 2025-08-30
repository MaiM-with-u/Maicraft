import json
from typing import Any


def translate_move_tool_result(result: Any, arguments: Any = None) -> str:
    """
    翻译move工具的执行结果，使其更可读
    
    Args:
        result: move工具的执行结果
        arguments: 工具调用参数，用于提供更准确的错误信息
        
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
        
        # 提取关键信息
        ok = result_data.get("ok", False)
        data = result_data.get("data", {})
        
        move_fail_str = ""
        
        if not ok:
            # 处理移动失败的情况
            error_msg = result_data.get("error", "")
            if "MOVE_FAILED" in error_msg:
                if "Took to long to decide path to goal" in error_msg:
                    # 根据工具参数提供更准确的错误信息
                    if "block" in arguments:
                        block_name = arguments["block"]
                        return f"移动失败: 这附近没有{block_name}"
                    elif "type" in arguments and arguments["type"] == "coordinate":
                        return "移动失败: 指定坐标太远了，无法到达"
                    return "移动失败: 这附近没有目标"
                else:
                    move_fail_str = "未到达目标点，可能是目标点无法到达"
            else:
                return f"移动失败，但不是MOVE_FAILED错误: {error_msg}"
        
        # 提取移动信息
        # target 字段暂未使用，保留解析但不赋值避免未使用告警
        distance = data.get("distance", 0)
        position = data.get("position", {})
        
        # 格式化位置信息
        x = position.get("x", 0)
        y = position.get("y", 0)
        z = position.get("z", 0)
        
        # 构建可读文本
        readable_text = f"移动到坐标 ({x}, {y}, {z}) 附近，距离目标：{distance} 格\n{move_fail_str}"

        
        return readable_text
        
    except Exception:
        # 如果解析失败，返回原始结果
        return str(result)

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

def translate_mine_block_tool_result(result: Any) -> str:
    """
    翻译mine_block工具的执行结果，使其更可读
    
    Args:
        result: mine_block工具的执行结果
        
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
        
        # 提取关键信息
        ok = result_data.get("ok", False)
        data = result_data.get("data", {})
        
        if not ok:
            return "挖掘方块失败"
        
        # 检查是否有挖掘数据
        if "minedCount" in data:
            # print(data)
            mined_count = data["minedCount"]
            mined_blocks = data.get("minedBlocks", [])
            
            # 处理方块名称，如果是列表则显示所有方块，如果是字符串则直接使用
            if len(mined_blocks) > 0:
                if len(mined_blocks) == 1:
                    block_name = mined_blocks[0]
                else:
                    # 多个方块用顿号分隔
                    block_name = "、".join(mined_blocks)
            
            # 构建可读文本
            if mined_count == 1:
                readable_text = f"成功挖掘了1个{block_name}"
            else:
                readable_text = f"成功挖掘了{mined_count}个方块：{block_name}"
            
            return readable_text
        else:
            # 如果没有挖掘数据，返回原始结果
            return str(result)
        
    except Exception:
        # 如果解析失败，返回原始结果
        return str(result)
    
def translate_place_block_tool_result(result: Any, arguments: Any = None) -> str:
    """
    翻译place_block工具的执行结果，使其更可读
    """

    # 如果结果是字符串，尝试解析JSON
    if isinstance(result, str):
        try:
            result_data = json.loads(result)
        except json.JSONDecodeError:
            return str(result)
    else:
        result_data = result
        
    ok = result_data.get("ok", False)
    if not ok:
        return "放置方块失败"
    
    return "放置方块成功"
        

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


def translate_start_smelting_tool_result(result: Any) -> str:
    """
    翻译start_smelting工具的执行结果，使其更可读
    
    Args:
        result: start_smelting工具的执行结果
        
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
        
        # 检查是否是start_smelting工具的结果
        if not isinstance(result_data, dict):
            return str(result)
        
        # 提取关键信息
        ok = result_data.get("ok", False)
        data = result_data.get("data", {})
        
        if not ok:
            return "开始熔炼失败，可能是物品不存在或缺少熔炉"
        
        # 提取熔炼信息
        item_name = data.get("item", "未知物品")
        count = data.get("count", 1)
        furnace_position = data.get("furnacePosition", {})
        
        # 格式化熔炉位置信息
        x = furnace_position.get("x", 0)
        y = furnace_position.get("y", 0)
        z = furnace_position.get("z", 0)
        
        # 构建可读文本
        if count == 1:
            readable_text = f"成功开始熔炼1个{item_name}，熔炉位置：({x}, {y}, {z})"
        else:
            readable_text = f"成功开始熔炼{count}个{item_name}，熔炉位置：({x}, {y}, {z})"
        
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
        # result应该是来自parse_tool_result的result_content字符串
        if not isinstance(result, str):
            return str(result)
        
        # 解析JSON字符串
        try:
            result_data = json.loads(result)
        except json.JSONDecodeError:
            return str(result)
        
        # 检查是否是view_chest工具的结果
        if not isinstance(result_data, dict):
            return str(result)
        
        # 提取关键信息
        ok = result_data.get("ok", False)
        data = result_data.get("data", {})
        
        if not ok:
            return "查看箱子失败，可能是箱子不存在或无法访问"
        
        # 提取箱子信息
        block = data.get("block", {})
        container_info = data.get("containerInfo", {})
        
        # 获取箱子位置
        position = block.get("position", {})
        x = position.get("x", 0)
        y = position.get("y", 0)
        z = position.get("z", 0)
        
        # 获取箱子类型和朝向
        block_name = block.get("displayName", "箱子")
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
            if slot.get("name") != "air" and slot.get("count", 0) > 0:
                item_name = slot.get("displayName", slot.get("name", "未知物品"))
                count = slot.get("count", 1)
                slot_num = slot.get("slot", 0)
                
                if count == 1:
                    items.append(f"1个{item_name}")
                else:
                    items.append(f"{count}个{item_name}")
        
        # 构建可读文本
        readable_text = f"✅ 成功查看箱子\n"
        readable_text += f"位置: ({x}, {y}, {z})\n"
        readable_text += f"类型: {block_name} (朝向: {facing})\n"
        readable_text += f"容量: {total_slots}格，已占用: {occupied_slots}格，空闲: {empty_slots}格 ({occupancy_rate})\n"
        
        if items:
            readable_text += f"物品列表:\n"
            for item in items:
                readable_text += f"  {item}\n"
        else:
            readable_text += "箱子为空"
        
        return readable_text
        
    except Exception:
        # 如果解析失败，返回原始结果
        return str(result)


def translate_collect_smelted_items_tool_result(result: Any) -> str:
    """
    翻译collect_smelted_items工具的执行结果，使其更可读
    
    Args:
        result: collect_smelted_items工具的执行结果
        
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
        
        # 检查是否是collect_smelted_items工具的结果
        if not isinstance(result_data, dict):
            return str(result)
        
        # 提取关键信息
        ok = result_data.get("ok", False)
        data = result_data.get("data", {})
        
        if not ok:
            return "收集熔炼物品失败"
        
        # 提取收集信息
        items = data.get("items", [])
        total_count = data.get("totalCount", 0)
        furnace_position = data.get("furnacePosition", {})
        
        # 格式化熔炉位置信息
        x = furnace_position.get("x", 0)
        y = furnace_position.get("y", 0)
        z = furnace_position.get("z", 0)
        
        if not items:
            return f"从熔炉位置 ({x}, {y}, {z}) 收集物品，但没有收集到任何物品"
        
        # 构建物品列表文本
        item_texts = []
        for item in items:
            item_name = item.get("name", "未知物品")
            item_count = item.get("count", 1)
            if item_count == 1:
                item_texts.append(f"1个{item_name}")
            else:
                item_texts.append(f"{item_count}个{item_name}")
        
        items_str = "、".join(item_texts)
        
        # 构建可读文本
        readable_text = f"成功从熔炉位置 ({x}, {y}, {z}) 收集到：{items_str}，总计：{total_count}个物品"
        
        return readable_text
        
    except Exception:
        # 如果解析失败，返回原始结果
        return str(result)

def translate_view_furnace_result(result: Any) -> str:
    """
    翻译view_furnace工具的执行结果，使其更可读
    
    Args:
        result: view_furnace工具的执行结果，来自parse_tool_result的result_content
        
    Returns:
        翻译后的可读文本
    """
    try:
        # result应该是来自parse_tool_result的result_content字符串
        if not isinstance(result, str):
            return str(result)
        
        # 解析JSON字符串
        try:
            result_data = json.loads(result)
        except json.JSONDecodeError:
            return str(result)
        
        # 检查是否是view_furnace工具的结果
        if not isinstance(result_data, dict):
            return str(result)
        
        # 提取关键信息
        ok = result_data.get("ok", False)
        data = result_data.get("data", {})
        
        if not ok:
            return "查看熔炉失败，可能是熔炉不存在或无法访问"
        
        # 提取熔炉信息
        block = data.get("block", {})
        container_info = data.get("containerInfo", {})
        
        # 获取熔炉位置
        position = block.get("position", {})
        x = position.get("x", 0)
        y = position.get("y", 0)
        z = position.get("z", 0)
        
        # 获取熔炉类型和朝向
        block_name = block.get("displayName", "熔炉")
        properties = block.get("_properties", {})
        facing = properties.get("facing", "未知")
        lit = properties.get("lit", False)
        
        # 获取容器统计信息
        stats = container_info.get("stats", {})
        total_slots = stats.get("totalSlots", 0)
        occupied_slots = stats.get("occupiedSlots", 0)
        empty_slots = stats.get("emptySlots", 0)
        occupancy_rate = stats.get("occupancyRate", "0%")
        
        # 获取熔炉专用信息
        furnace_info = container_info.get("furnaceInfo", {})
        input_item = furnace_info.get("inputItem")
        fuel_item = furnace_info.get("fuelItem")
        output_item = furnace_info.get("outputItem")
        fuel = furnace_info.get("fuel", 0)
        progress = furnace_info.get("progress", 0)
        
        # 获取物品列表
        slots = container_info.get("slots", [])
        items = []
        
        for slot in slots:
            if slot.get("name") != "air" and slot.get("count", 0) > 0:
                item_name = slot.get("displayName", slot.get("name", "未知物品"))
                count = slot.get("count", 1)
                slot_num = slot.get("slot", 0)
                
                if count == 1:
                    items.append(f"槽位{slot_num}: 1个{item_name}")
                else:
                    items.append(f"槽位{slot_num}: {count}个{item_name}")
        
        # 构建可读文本
        readable_text = f"✅ 成功查看熔炉\n"
        readable_text += f"位置: ({x}, {y}, {z})\n"
        readable_text += f"类型: {block_name} (朝向: {facing})\n"
        readable_text += f"状态: {'正在燃烧' if lit else '未燃烧'}\n"
        readable_text += f"容量: {total_slots}格，已占用: {occupied_slots}格，空闲: {empty_slots}格 ({occupancy_rate})\n"
        
        # 添加熔炉专用信息
        if input_item:
            readable_text += f"输入物品: {input_item.get('displayName', input_item.get('name', '未知物品'))}\n"
        if fuel_item:
            readable_text += f"燃料: {fuel_item.get('displayName', fuel_item.get('name', '未知物品'))}\n"
        if output_item:
            readable_text += f"输出物品: {output_item.get('displayName', output_item.get('name', '未知物品'))}\n"
        
        if fuel > 0:
            readable_text += f"燃料剩余: {fuel}%\n"
        if progress > 0:
            readable_text += f"熔炼进度: {progress}%\n"
        
        if items:
            readable_text += f"物品列表:\n"
            for item in items:
                readable_text += f"  {item}\n"
        else:
            readable_text += "熔炉为空"
        
        return readable_text
        
    except Exception:
        # 如果解析失败，返回原始结果
        return str(result)

def translate_use_chest_tool_result(result: Any) -> str:
    """
    翻译use_chest工具的执行结果，使其更可读
    
    Args:
        result: use_chest工具的执行结果
        
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
        
        # 检查是否是use_chest工具的结果
        if not isinstance(result_data, dict):
            return str(result)
        
        # 提取关键信息
        ok = result_data.get("ok", False)
        data = result_data.get("data", {})
        
        if not ok:
            # 处理操作失败的情况
            error_code = result_data.get("error_code", "")
            error_message = result_data.get("error_message", "")
            
            if "ALL_OPERATIONS_FAILED" in error_code:
                # 处理复杂的失败情况
                if "访问了" in error_message and "箱子" in error_message:
                    # 解析箱子访问统计信息
                    import re
                    
                    # 提取访问的箱子数量
                    chest_match = re.search(r'访问了\s*(\d+)\s*个箱子', error_message)
                    chest_count = chest_match.group(1) if chest_match else "未知"
                    
                    # 提取成功和失败操作次数
                    success_match = re.search(r'成功操作:\s*(\d+)\s*次', error_message)
                    success_count = success_match.group(1) if success_match else "0"
                    
                    failure_match = re.search(r'失败操作:\s*(\d+)\s*次', error_message)
                    failure_count = failure_match.group(1) if failure_match else "0"
                    
                    # 提取未能完全取出的物品信息
                    withdraw_match = re.search(r'未能完全取出:\s*(\w+)\((\d+)\)', error_message)
                    if withdraw_match:
                        item_name = withdraw_match.group(1)
                        needed_count = withdraw_match.group(2)
                        readable_text = f"❌ 附近箱子物品不足\n"
                        readable_text += f"需要取出: {item_name} ({needed_count}个)\n"
                        readable_text += f"访问了 {chest_count} 个箱子，但都没有足够的{item_name}"
                        return readable_text
                    else:
                        return f"❌ 箱子操作失败: {error_message}"
                elif "背包没有" in error_message:
                    # 提取物品名称
                    match = re.search(r'背包没有\s*(\w+)', error_message)
                    if match:
                        item_name = match.group(1)
                        return f"❌ 操作失败: 背包中没有{item_name}"
                    else:
                        return f"❌ 操作失败: {error_message}"
                else:
                    return f"❌ 操作失败: {error_message}"
            else:
                return f"❌ 操作失败: {error_message}"
        
        # 提取操作结果信息
        operation_results = data.get("operationResults", [])
        chest_contents = data.get("chestContents", [])
        chest_location = data.get("chestLocation", {})
        
        # 构建可读文本
        readable_text = "✅ 箱子操作成功\n"
        
        # 添加操作结果
        if operation_results:
            readable_text += "操作结果:\n"
            for operation in operation_results:
                readable_text += f"  {operation}\n"
        
        # 添加箱子位置信息
        if chest_location:
            x = chest_location.get("x", 0)
            y = chest_location.get("y", 0)
            z = chest_location.get("z", 0)
            readable_text += f"箱子位置: ({x}, {y}, {z})\n"
        
        # 添加箱子内容信息
        if chest_contents:
            readable_text += "箱子内容:\n"
            for item in chest_contents:
                item_name = item.get("name", "未知物品")
                count = item.get("count", 1)
                if count == 1:
                    readable_text += f"  {item_name}: 1个\n"
                else:
                    readable_text += f"  {item_name}: {count}个\n"
        else:
            readable_text += "箱子为空\n"
        
        return readable_text
        
    except Exception:
        # 如果解析失败，返回原始结果
        return str(result)