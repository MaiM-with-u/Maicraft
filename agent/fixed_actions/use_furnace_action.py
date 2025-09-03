from typing import Optional, Tuple
from mcp_server.client import global_mcp_client
from agent.utils.utils import parse_tool_result
from agent.utils.utils_tool_translation import translate_use_furnace_tool_result
from agent.environment.basic_info import Item


async def use_furnace(x: int, y: int, z: int, action: str, item: str, count: int, slot: str) -> Tuple[bool, Optional[Item], Optional[Item], Optional[Item], str]:
    """
    对指定坐标的熔炉执行操作。
    参数:
      - action: 仅支持 "put" 或 "take"
      - items: [{"name": str, "count": int, "position": str}]，position 为槽位 input/fuel/output
    返回:
      - ok: 是否成功
      - input_item: 输入槽物品
      - output_item: 输出槽物品
      - fuel_item: 燃料槽物品
      - text: 可读描述
    """
    # 仅允许 put/take
    if action not in ("put", "take"):
        action = "put"

    # 验证 items 格式并确保每个 item 都有 position

    items = [{"name": item, "count": count or 1, "position": slot}]
    
    args = {"action": action, "items": items, "x": x, "y": y, "z": z}
    call_result = await global_mcp_client.call_tool_directly("use_furnace", args)
    ok, result_content = parse_tool_result(call_result)

    text = translate_use_furnace_tool_result(result_content)

    # 使用 query_block 统一获取熔炉当前槽位内容
    input_item: Optional[Item] = None
    output_item: Optional[Item] = None
    fuel_item: Optional[Item] = None

    try:
        q_args = {"x": x, "y": y, "z": z, "includeContainerInfo": True}
        q_res = await global_mcp_client.call_tool_directly("query_block", q_args)
        _, q_content = parse_tool_result(q_res)
        import json
        payload = json.loads(q_content) if isinstance(q_content, str) else q_content
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        c_info = data.get("containerInfo", {}) if isinstance(data, dict) else {}
        slots = c_info.get("slots", []) if isinstance(c_info, dict) else []
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
    except Exception:
        pass

    return ok, input_item, output_item, fuel_item, text


