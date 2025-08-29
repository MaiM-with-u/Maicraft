#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试合成脚本
- 参考 mcp_tools_browser.py 的连接方式，自动启动真实的 MCP 服务器
- 读取玩家背包/状态
- 查询原始配方 (query_raw_recipe) 并解析为 RawRecipe
- 可选执行 craft_item 进行真实合成
"""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional
from pathlib import Path
import argparse  # noqa: F401

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.logger import get_logger,setup_logging  # type: ignore  # noqa: E402
from mcp_server.client import MCPClient  # type: ignore  # noqa: E402
from agent.action.craft_action.recipe_class import RawRecipe  # type: ignore  # noqa: E402
from agent.action.craft_action.craft_action import RecipeFinder  # type: ignore  # noqa: E402
from agent.environment import EnvironmentInfo, global_environment  # type: ignore  # noqa: E402
from agent.environment_updater import EnvironmentUpdater  # type: ignore  # noqa: E402

setup_logging("DEBUG")

logger = get_logger("TestCrafting")


def _safe_parse_json(text: str) -> Optional[Dict[str, Any]]:
    try:
        import dirtyjson
        return dirtyjson.loads(text)
    except Exception:
        try:
            return json.loads(text)
        except Exception:
            return None


async def connect_mcp() -> MCPClient:
    """连接并启动 MCP 服务器 (通过 npx maicraft@latest)。"""
    client = MCPClient()
    ok = await client.connect()
    if not ok:
        raise RuntimeError("连接 MCP 服务器失败")
    logger.info("成功连接到 MCP 服务器")
    return client


def _extract_text(result: Any) -> str:
    text = ""
    if hasattr(result, "content") and result.content:
        for c in result.content:
            if hasattr(c, "text"):
                text += c.text
    return text


async def call_tool_json(client: MCPClient, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """执行工具并尽力解析为 JSON dict。失败则返回空 dict。"""
    result = await client.call_tool_directly(name, params)
    text = _extract_text(result)
    payload = _safe_parse_json(text) or {}
    # 兜底兼容 structured_content / data
    if not payload and hasattr(result, "structured_content") and result.structured_content:
        try:
            if isinstance(result.structured_content, dict):
                payload = result.structured_content
        except Exception:
            pass
    if not payload and hasattr(result, "data") and result.data:
        try:
            if isinstance(result.data, dict):
                payload = result.data
        except Exception:
            pass
    return payload


def get_inventory_from_env() -> List[Dict[str, Any]]:
    """直接从全局环境读取已标准化的背包数据。"""
    inv = global_environment.inventory or []
    return [dict(item) if isinstance(item, dict) else item for item in inv]

def pretty_print_inventory(inv: List[Dict[str, Any]]) -> str:
    if not inv:
        return "  物品栏为空"
    lines: List[str] = []
    for item in sorted(inv, key=lambda x: x.get("slot", 0)):
        if isinstance(item, dict):
            name = item.get("name", "?")
            cnt = item.get("count", 0)
            slot = item.get("slot", 0)
            lines.append(f"  [槽位{slot:02d}] {name} x{cnt}")
        else:
            lines.append(f"  {str(item)}")
    return "\n".join(lines)


def get_player_position_from_env() -> Optional[Dict[str, float]]:
    """从全局环境读取玩家位置 {x,y,z}。失败返回 None。"""
    bp = getattr(global_environment, "block_position", None)
    if bp is None:
        return None
    try:
        return {"x": float(bp.x), "y": float(bp.y), "z": float(bp.z)}
    except Exception:
        return None


async def main():
    # 先连接 MCP，之后再解析/询问参数
    client = await connect_mcp()
    try:
        updater = EnvironmentUpdater(mcp_client=client,update_interval=0.1)
        # updater.start()
        await updater.perform_update()
        
        # 合成前背包
        await updater.perform_update()
        inv_before = get_inventory_from_env()
        print("\n=== 合成前背包 ===")
        print(pretty_print_inventory(inv_before))
        
        
        print("进入交互模式：按提示输入参数，直接回车使用默认值。")
        try:
            item_name = input("目标物品名称 (如 oak_planks): ").strip()
            while not item_name:
                print("物品名称不能为空。")
                item_name = input("目标物品名称 (如 oak_planks): ").strip()
            count_str = input("合成数量(默认 1): ").strip()
            if count_str:
                try:
                    count = max(1, int(count_str))
                except Exception:
                    print("数量无效，使用默认 1")
                    count = 1
            else:
                count = 1
        except KeyboardInterrupt:
            print("\n用户中断")
            return


        rf = RecipeFinder(mcp_client=client)
        while True:
            # 获取玩家位置用于检测附近工作台（可选）
            pos = get_player_position_from_env()
            if pos is not None:
                from types import SimpleNamespace
                block_position = SimpleNamespace(x=pos["x"], y=pos["y"], z=pos["z"])
            else:
                block_position = None
            
            await updater.perform_update()
            inv_before = get_inventory_from_env()

            ok, summary = await rf.craft_item_smart(item_name, int(count), inv_before, block_position)
            print("\n=== craft_item_smart 结果 ===")
            print("成功" if ok else "失败")
            print(summary)

            # 合成后背包
            await updater.perform_update()
            inv_after = get_inventory_from_env()
            print("\n=== 合成后背包 ===")
            print(pretty_print_inventory(inv_after))

            # 显示差异
            try:
                diff_text = EnvironmentInfo.get_inventory_diff_text(inv_before, inv_after)
                print("\n=== 背包变化 ===")
                print(diff_text)
            except Exception:
                pass
            
            await updater.perform_update()

            # 询问是否继续合成
            try:
                cont = input("\n继续合成? [回车=再次相同 / c=修改物品与数量 / q=退出]: ").strip().lower()
            except KeyboardInterrupt:
                print("\n用户中断，退出")
                break

            if cont in ("q", "quit", "n", "no", "否"):
                break
            if cont in ("c", "change", "修改"):
                try:
                    new_item = input("目标物品名称: ").strip()
                    if new_item:
                        item_name = new_item
                    new_count = input("合成数量(默认 1): ").strip()
                    if new_count:
                        count = max(1, int(new_count))
                except Exception:
                    print("输入无效，保持原设置")
                continue
            # 其它输入（含空）默认再次执行同一合成
            continue
        
    except Exception as e:
        print(f"程序异常: {e}")
        import traceback
        traceback.print_exc()

    finally:
        
        await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"程序异常: {e}")
        import traceback
        traceback.print_exc()


