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
            mined_count = data["minedCount"]
            block_name = data.get("blockName", "未知方块")

            
            # 构建可读文本
            if mined_count == 1:
                readable_text = f"成功挖掘了1个{block_name}"
            else:
                readable_text = f"成功挖掘了{mined_count}个{block_name}"
            
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