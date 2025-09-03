from agent.block_cache.block_cache import global_block_cache
from agent.utils.utils import parse_tool_result
from agent.utils.utils_tool_translation import translate_view_chest_result, translate_view_furnace_result
from mcp_server.client import global_mcp_client
from typing import Optional
from agent.environment.basic_info import Item


async def view_chest(x: int, y: int, z: int) -> tuple[bool, list[Item], int, str]:
    block_cache = global_block_cache.get_block(x, y, z)
    if block_cache.block_type != "chest":
        return False, [], 0, f"位置{x},{y},{z}不是箱子，无法查看{block_cache.block_type}"

    args = {"x": x, "y": y, "z": z, "includeContainerInfo": True}
    call_result = await global_mcp_client.call_tool_directly("query_block", args)
    is_success, result_content = parse_tool_result(call_result)

    if not is_success:
        return False, [], 0, f"查看箱子失败: {result_content}"

    # 解析 result_content 获取物品与剩余空间
    import json
    try:
        payload = json.loads(result_content) if isinstance(result_content, str) else result_content
    except Exception:
        payload = {}
    data_obj = payload.get("data", {}) if isinstance(payload, dict) else {}
    container_info = data_obj.get("containerInfo", {}) if isinstance(data_obj, dict) else {}
    stats = container_info.get("stats", {}) if isinstance(container_info, dict) else {}
    empty_slots = int(stats.get("emptySlots", 0)) if isinstance(stats, dict) else 0
    slots = container_info.get("slots", []) if isinstance(container_info, dict) else []

    items: list[Item] = []
    for s in slots or []:
        try:
            name = s.get("name")
            count = int(s.get("count", 0))
            slot_idx = int(s.get("slot", 0))
            if name and name != "air" and count > 0:
                items.append(Item(name=name, count=count, slot=slot_idx))
        except Exception:
            continue

    result_str = translate_view_chest_result(result_content)
    return True, items, empty_slots, result_str


async def view_furnace(x: int, y: int, z: int) -> tuple[bool, Optional[Item], Optional[Item], Optional[Item], str]:
    block_cache = global_block_cache.get_block(x, y, z)
    if block_cache.block_type not in ("furnace", "blast_furnace", "smoker"):
        return False, None, None, None, f"位置{x},{y},{z}不是熔炉(furnace/blast_furnace/smoker)，无法查看{block_cache.block_type}"

    args = {"x": x, "y": y, "z": z, "includeContainerInfo": True}
    call_result = await global_mcp_client.call_tool_directly("query_block", args)
    is_success, result_content = parse_tool_result(call_result)

    if not is_success:
        return False, None, None, None, f"查看熔炉失败: {result_content}"

    # 解析槽位，0: input, 1: fuel, 2: output
    import json
    try:
        payload = json.loads(result_content) if isinstance(result_content, str) else result_content
    except Exception:
        payload = {}
    data_obj = payload.get("data", {}) if isinstance(payload, dict) else {}
    container_info = data_obj.get("containerInfo", {}) if isinstance(data_obj, dict) else {}
    slots = container_info.get("slots", []) if isinstance(container_info, dict) else []

    input_item: Optional[Item] = None
    fuel_item: Optional[Item] = None
    output_item: Optional[Item] = None
    for s in slots or []:
        try:
            name = s.get("name")
            count = int(s.get("count", 0))
            slot_idx = int(s.get("slot", -1))
            if name and name != "air" and count > 0:
                it = Item(name=name, count=count, slot=slot_idx)
                if slot_idx == 0:
                    input_item = it
                elif slot_idx == 1:
                    fuel_item = it
                elif slot_idx == 2:
                    output_item = it
        except Exception:
            continue

    result_str = translate_view_furnace_result(result_content)
    return True, input_item, output_item, fuel_item, result_str


async def view_container(x: int, y: int, z: int, type: str):
    if type == "chest":
        return await view_chest(x, y, z)
    elif type in ("furnace", "blast_furnace", "smoker"):
        return await view_furnace(x, y, z)
    else:
        return False, None, None, None, f"方块{type}的位置{x},{y},{z}，不是chest，也不是熔炉(furnace/blast_furnace/smoker)，无法查看"


