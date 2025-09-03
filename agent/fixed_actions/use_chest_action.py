from typing import List, Tuple
from mcp_server.client import global_mcp_client
from agent.utils.utils import parse_tool_result
from agent.utils.utils_tool_translation import translate_use_chest_tool_result
from agent.environment.basic_info import Item


async def use_chest(x: int, y: int, z: int, action: str, item:str ,count:int) -> Tuple[bool, List[Item], int, str]:
    """
    对指定坐标的箱子进行存取操作。
    参数:
      - action: "store" 或 "withdraw"
      - item: 物品名称
      - count: 物品数量
    返回:
      - ok: 操作是否成功
      - items: 箱子当前物品列表（操作后）
      - remaining_slots: 剩余空槽位数
      - text: 可读文本
    """
    items = [{"name": item, "count": count}]
    args = {"items": items, "action": action, "x": x, "y": y, "z": z}
    call_result = await global_mcp_client.call_tool_directly("use_chest", args)
    ok, result_content = parse_tool_result(call_result)

    text = translate_use_chest_tool_result(result_content)

    # 解析 items 与 remaining_slots
    import json
    parsed = None
    try:
        parsed = json.loads(result_content) if isinstance(result_content, str) else result_content
    except Exception:
        parsed = None

    items_out: List[Item] = []
    remaining_slots: int = 0

    if isinstance(parsed, dict):
        data = parsed.get("data", {}) or {}
        # 优先从 use_chest 的 data 中读取箱子内容
        chest_contents = data.get("chestContents", []) or []
        for it in chest_contents:
            try:
                name = it.get("name")
                count = int(it.get("count", 0))
                slot = int(it.get("slot", 0)) if it.get("slot") is not None else 0
                if name and name != "air" and count > 0:
                    items_out.append(Item(name=name, count=count, slot=slot))
            except Exception:
                continue

        # 如果工具返回了统计信息，尝试读取剩余槽位；否则尝试 query_block 获取
        stats = data.get("stats") if isinstance(data, dict) else None
        if isinstance(stats, dict):
            remaining_slots = int(stats.get("emptySlots", 0) or 0)

    # 若未能获取 remaining_slots，则补充调用 query_block 读取容器统计
    if remaining_slots == 0:
        try:
            q_args = {"x": x, "y": y, "z": z, "includeContainerInfo": True}
            q_res = await global_mcp_client.call_tool_directly("query_block", q_args)
            _, q_content = parse_tool_result(q_res)
            q_parsed = json.loads(q_content) if isinstance(q_content, str) else q_content
            if isinstance(q_parsed, dict):
                q_data = q_parsed.get("data", {}) or {}
                c_info = q_data.get("containerInfo", {}) or {}
                stats = c_info.get("stats", {}) or {}
                remaining_slots = int(stats.get("emptySlots", 0) or 0)
                # 若之前 items_out 为空，使用 query_block 的 slots 补齐
                if not items_out:
                    slots = c_info.get("slots", []) or []
                    for s in slots:
                        try:
                            name = s.get("name")
                            count = int(s.get("count", 0))
                            slot = int(s.get("slot", 0))
                            if name and name != "air" and count > 0:
                                items_out.append(Item(name=name, count=count, slot=slot))
                        except Exception:
                            continue
        except Exception:
            pass

    return ok, items_out, remaining_slots, text


