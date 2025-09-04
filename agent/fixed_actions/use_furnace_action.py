from typing import Optional, Tuple
from mcp_server.client import global_mcp_client
from agent.utils.utils import parse_tool_result
from agent.utils.utils_tool_translation import translate_use_furnace_tool_result
from agent.environment.basic_info import Item


async def use_furnace(x: int, y: int, z: int, action: str, item: str, count: int, slot: str) -> Tuple[bool, Optional[Item]]:
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

    slot_item = None
    container_content = result_content.get("containerContents", [])
    for content in container_content:
        if content.get("slot") == slot:
            slot_item = content
            break
    
    slot_item = Item(name=slot_item.get("name"), count=slot_item.get("count"))
    return ok, slot_item


