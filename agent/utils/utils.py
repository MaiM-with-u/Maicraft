import json
import math
from json_repair import repair_json
from typing import List, Dict, Any
from utils.logger import get_logger
from mcp_server.client import CallToolResult
from agent.common.basic_class import BlockPosition
from agent.to_do_list import mai_done_list

logger = get_logger("Utils")

def parse_json(text: str) -> dict:
    """解析json字符串"""
    try:
        repaired_json = repair_json(text)
        return json.loads(repaired_json)
    except json.JSONDecodeError:
        return None
    
def convert_mcp_tools_to_openai_format(mcp_tools) -> List[Dict[str, Any]]:
    """将MCP工具转换为OpenAI工具格式"""
    openai_tools = []
    
    for tool in mcp_tools:
        # 构建工具描述
        description = tool.description or f"执行{tool.name}操作"
        if tool.inputSchema:
            properties = tool.inputSchema.get("properties", {})
            required = tool.inputSchema.get("required", [])
            
            # 添加参数信息到描述
            if properties:
                description += "\n\n参数说明："
                for prop_name, prop_info in properties.items():
                    prop_type = prop_info.get("type", "string")
                    prop_desc = prop_info.get("description", "")
                    required_mark = " (必需)" if prop_name in required else " (可选)"
                    description += f"\n- {prop_name}: {prop_type}{required_mark}"
                    if prop_desc:
                        description += f" - {prop_desc}"
        
        openai_tool = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": description,
                "parameters": tool.inputSchema or {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        openai_tools.append(openai_tool)
    
    return openai_tools

def calculate_distance(position1: BlockPosition, position2: BlockPosition) -> float:
    """计算两个位置之间的距离"""
    return math.sqrt((position1.x - position2.x)**2 + (position1.y - position2.y)**2 + (position1.z - position2.z)**2)


def parse_tool_result(result: CallToolResult) -> tuple[bool, str]:
    """解析工具执行结果，判断是否真的成功
    
    Args:
        result: MCP工具返回的结果
        
    Returns:
        (是否成功, 结果内容)
    """
    try:
        # 首先检查MCP层面的错误
        if result.is_error:
            structured_content = result.structured_content
            if structured_content and structured_content.get("interrupt"):
                return False, f"动作被中断: {structured_content.get('interrupt_reason')}"
            
            
            return False, f"MCP错误: {result.content}"
    
        result_json = result.structured_content
        
        # logger.info(f"工具执行结果: {result_json}")
    
        # 检查ok字段
        if "ok" in result_json:
            if result_json["ok"] is False:
                error_msg = result_json.get("error_message", "未知错误")
                error_code = result_json.get("error_code", "")
                return False, f"工具执行失败: {error_msg} (错误代码: {error_code})"
            elif result_json["ok"] is True:
                return True, result_json.get("data", {})
        
        # 检查success字段
        if "success" in result_json:
            if result_json["success"] is False:
                error_msg = result_json.get("error_message", "未知错误")
                error_code = result_json.get("error_code", "")
                return False, f"工具执行失败: {error_msg} (错误代码: {error_code})"
            elif result_json["success"] is True:
                return True, result_json.get("data", {})
        
        # 检查error_code字段
        if "error_code" in result_json and result_json["error_code"]:
            error_msg = result_json.get("error_message", "未知错误")
            error_code = result_json["error_code"]
            return False, f"工具执行失败: {error_msg} (错误代码: {error_code})"
        
        # 默认认为成功
        return True, result_json.get("data", {})
    except Exception as e:
        logger.error(f"[MaiAgent] 解析工具执行结果时异常: {e}")
        return False, f"工具执行失败: {e}"
    
    

def filter_action_tools(available_tools) -> List:
    """过滤工具，只保留动作类工具，排除查询类工具
    
    Args:
        available_tools: 所有可用的MCP工具列表
        
    Returns:
        过滤后的动作类工具列表
    """
    # 定义查询类工具名称（需要排除的工具）
    query_tool_names = {
        "query_game_state", # 查询游戏状态
        "query_player_status", # 查询玩家状态
        "query_recent_events", # 查询最近事件
        "query_recipe", # 查询配方
        "query_surroundings", # 查询周围环境
    }
    
    filtered_tools = []
    
    for tool in available_tools:
        tool_name = tool.name.lower() if tool.name else ""
        
        # 如果工具名称在查询类工具列表中，则跳过
        if tool_name in query_tool_names:
            logger.debug(f"[Utils] 排除查询类工具: {tool.name}")
            continue
        
        filtered_tools.append(tool)
    
    return filtered_tools


def format_task_done_list() -> str:
    """将任务执行记录翻译成可读文本，只取最近10条。

    任务记录为 (success: bool, task_id: str, message: str)
    """
    if not mai_done_list:
        return "暂无任务执行记录"

    lines: list[str] = []
    # 仅取最近10条
    for success, task_id, message in mai_done_list[-10:]:
        status_text = "成功" if success else "失败"
        # 规避 None/空值
        safe_task_id = str(task_id) if task_id is not None else ""
        safe_message = str(message) if message is not None else ""
        lines.append(f"任务ID {safe_task_id}：{status_text}（{safe_message}）")

    return "\n".join(lines)

def parse_thinking(thinking: str) -> tuple[bool, str, dict, str]:
    """
    解析思考结果
    1. 先解析thinking中有没有json，如果有，就获取第一个json的完整内容
    2. 拆分出第一个json前所有内容
    返回: (是否成功, 思考结果, 第一个json对象, json前内容)
    """
    # 匹配第一个json对象（支持嵌套大括号）
    def find_first_json(text):
        stack = []
        start = None
        for i, c in enumerate(text):
            if c == '{':
                if not stack:
                    start = i
                stack.append('{')
            elif c == '}':
                if stack:
                    stack.pop()
                    if not stack and start is not None:
                        return text[start:i+1], start, i+1
        return None, None, None

    json_obj = None
    json_str, json_start, json_end = find_first_json(thinking)
    json_before = ""
    success = False
    
    if json_str:
        json_before = thinking[:json_start].strip()
        try:
            json_obj = parse_json(json_str)
            success = True
        except Exception as e:
            logger.error(f"[Utils] 解析思考结果时异常: {json_str}, 错误: {e}")
            # 尝试修复不完整的JSON
            try:
                # 如果JSON不完整，尝试添加缺失的大括号
                if not json_str.strip().endswith('}'):
                    # 计算缺失的大括号数量
                    open_braces = json_str.count('{')
                    close_braces = json_str.count('}')
                    missing_braces = open_braces - close_braces
                    if missing_braces > 0:
                        fixed_json = json_str + '}' * missing_braces
                        json_obj = parse_json(fixed_json)
                        success = True
                        logger.info(f"[Utils] 修复了不完整的JSON: {fixed_json}")
            except Exception as fix_e:
                logger.error(f"[Utils] 修复JSON失败: {fix_e}")
    else:
        json_before = thinking.strip()

    # 移除json_before中的 ```json 和 ```
    if "```json" in json_before:
        json_before = json_before.replace("```json", "")
    if "```" in json_before:
        json_before = json_before.replace("```", "")

    # 移除json_before的所有换行符
    json_before = json_before.replace('\n', '')
    
    
    action_type = json_obj.get("action_type")
    if not action_type:
        logger.error(f" 思考结果中没有action_type: {thinking}")
        return False, thinking, json_obj, json_before

    return success, thinking, json_obj, json_before


def parse_thinking_multiple(thinking: str) -> tuple[bool, str, list, str]:
    """
    解析思考结果中的多个JSON动作
    1. 解析thinking中所有的json对象
    2. 拆分出所有json前的内容
    返回: (是否成功, 思考结果, json对象列表, json前内容)
    """
    def find_all_jsons(text):
        """找到所有完整的JSON对象"""
        jsons = []
        stack = []
        start = None
        i = 0
        
        while i < len(text):
            c = text[i]
            if c == '{':
                if not stack:
                    start = i
                stack.append('{')
            elif c == '}':
                if stack:
                    stack.pop()
                    if not stack and start is not None:
                        json_str = text[start:i+1]
                        jsons.append((json_str, start, i+1))
                        start = None
            i += 1
        
        return jsons
    
    json_objects = []
    json_before = ""
    success = False
    
    # 找到所有JSON对象
    all_jsons = find_all_jsons(thinking)
    
    if all_jsons:
        # 获取第一个JSON前的内容
        first_json_start = all_jsons[0][1]
        json_before = thinking[:first_json_start].strip()
        
        # 解析所有JSON对象
        for json_str, start, end in all_jsons:
            try:
                json_obj = parse_json(json_str)
                if json_obj:
                    json_objects.append(json_obj)
                    success = True
                else:
                    logger.warning(f"[Utils] JSON解析结果为空: {json_str}")
            except Exception as e:
                logger.error(f"[Utils] 解析JSON对象时异常: {json_str}, 错误: {e}")
    else:
        json_before = thinking.strip()
    
    # 移除json_before中的 ```json 和 ```
    if "```json" in json_before:
        json_before = json_before.replace("```json", "")
    if "```" in json_before:
        json_before = json_before.replace("```", "")
    
    return success, thinking, json_objects, json_before


def compare_inventories(old_inventory: List[Dict[str, Any]], new_inventory: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    比较两个inventory的差异
    
    Args:
        old_inventory: 旧的物品栏列表
        new_inventory: 新的物品栏列表
        
    Returns:
        包含差异信息的字典:
        {
            'added': [{'name': '物品名', 'count': 数量, 'slot': 槽位}],
            'removed': [{'name': '物品名', 'count': 数量, 'slot': 槽位}],
            'changed': [{'name': '物品名', 'old_count': 旧数量, 'new_count': 新数量, 'slot': 槽位}],
            'summary': '差异摘要文本'
        }
    """
    # 创建物品名称到物品信息的映射，用于快速查找
    old_items = {}
    new_items = {}
    
    # 处理旧物品栏
    for item in old_inventory:
        if isinstance(item, dict) and 'name' in item and item['name']:
            item_name = item['name']
            if item_name not in old_items:
                old_items[item_name] = []
            old_items[item_name].append({
                'name': item_name,
                'count': item.get('count', 0),
                'slot': item.get('slot', 0)
            })
    
    # 处理新物品栏
    for item in new_inventory:
        if isinstance(item, dict) and 'name' in item and item['name']:
            item_name = item['name']
            if item_name not in new_items:
                new_items[item_name] = []
            new_items[item_name].append({
                'name': item_name,
                'count': item.get('count', 0),
                'slot': item.get('slot', 0)
            })
    
    added = []
    removed = []
    changed = []
    
    # 检查新增的物品
    for item_name, new_item_list in new_items.items():
        if item_name not in old_items:
            # 完全新增的物品
            for new_item in new_item_list:
                added.append(new_item.copy())
        else:
            # 检查数量变化
            old_item_list = old_items[item_name]
            
            # 简单的数量比较（假设相同名称的物品数量变化）
            old_total_count = sum(item['count'] for item in old_item_list)
            new_total_count = sum(item['count'] for item in new_item_list)
            
            if new_total_count > old_total_count:
                # 数量增加
                added.append({
                    'name': item_name,
                    'count': new_total_count - old_total_count,
                    'slot': 'multiple'  # 多个槽位
                })
            elif new_total_count < old_total_count:
                # 数量减少
                removed.append({
                    'name': item_name,
                    'count': old_total_count - new_total_count,
                    'slot': 'multiple'  # 多个槽位
                })
            
            # 检查具体槽位的变化
            for new_item in new_item_list:
                new_slot = new_item['slot']
                new_count = new_item['count']
                
                # 查找相同槽位的旧物品
                old_item_in_slot = None
                for old_item in old_item_list:
                    if old_item['slot'] == new_slot:
                        old_item_in_slot = old_item
                        break
                
                if old_item_in_slot is None:
                    # 这个槽位新增了物品
                    added.append(new_item.copy())
                elif old_item_in_slot['count'] != new_count:
                    # 这个槽位的物品数量发生了变化
                    changed.append({
                        'name': item_name,
                        'old_count': old_item_in_slot['count'],
                        'new_count': new_count,
                        'slot': new_slot
                    })
    
    # 检查移除的物品
    for item_name, old_item_list in old_items.items():
        if item_name not in new_items:
            # 完全移除的物品
            for old_item in old_item_list:
                removed.append(old_item.copy())
        else:
            # 检查具体槽位的移除
            new_item_list = new_items[item_name]
            for old_item in old_item_list:
                old_slot = old_item['slot']
                
                # 查找相同槽位的新物品
                new_item_in_slot = None
                for new_item in new_item_list:
                    if new_item['slot'] == old_slot:
                        new_item_in_slot = new_item
                        break
                
                if new_item_in_slot is None:
                    # 这个槽位的物品被移除了
                    removed.append(old_item.copy())
    
    # 生成摘要文本
    summary_parts = []
    if added:
        added_summary = ", ".join([f"{item['name']}x{item['count']}" for item in added])
        summary_parts.append(f"新增: {added_summary}")
    
    if removed:
        removed_summary = ", ".join([f"{item['name']}x{item['count']}" for item in removed])
        summary_parts.append(f"减少: {removed_summary}")
    
    if changed:
        changed_summary = ", ".join([f"{item['name']} {item['old_count']}→{item['new_count']}" for item in changed])
        summary_parts.append(f"变化: {changed_summary}")
    
    if not summary_parts:
        summary = "物品栏没有变化"
    else:
        summary = "; ".join(summary_parts)
    
    return {
        'added': added,
        'removed': removed,
        'changed': changed,
        'summary': summary
    }


def get_inventory_diff_text(old_inventory: List[Dict[str, Any]], new_inventory: List[Dict[str, Any]]) -> str:
    """
    获取两个inventory差异的可读文本
    
    Args:
        old_inventory: 旧的物品栏列表
        new_inventory: 新的物品栏列表
        
    Returns:
        格式化的差异文本
    """
    diff = compare_inventories(old_inventory, new_inventory)
    
    lines = ["【物品栏变化】"]
    
    if diff['added']:
        lines.append("新增物品:")
        for item in diff['added']:
            slot_info = f" (槽位{item['slot']})" if item['slot'] != 'multiple' else ""
            lines.append(f"  + {item['name']} x{item['count']}{slot_info}")
    
    if diff['removed']:
        lines.append("减少物品:")
        for item in diff['removed']:
            slot_info = f" (槽位{item['slot']})" if item['slot'] != 'multiple' else ""
            lines.append(f"  - {item['name']} x{item['count']}{slot_info}")
    
    if diff['changed']:
        lines.append("数量变化:")
        for item in diff['changed']:
            lines.append(f"  {item['name']}: {item['old_count']} → {item['new_count']} (槽位{item['slot']})")
    
    if not any([diff['added'], diff['removed'], diff['changed']]):
        lines.append("物品栏没有变化")
    
    return "\n".join(lines)