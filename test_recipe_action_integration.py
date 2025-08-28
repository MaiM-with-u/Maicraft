import asyncio
from typing import List, Any

from src.plugins.maicraft.mcp.client import MCPClient
from src.plugins.maicraft.agent.block_cache.block_cache import global_block_cache, BlockPosition
from src.plugins.maicraft.agent.environment_updater import EnvironmentUpdater
from src.plugins.maicraft.agent.environment import global_environment
from src.plugins.maicraft.agent.action.recipe_action import RecipeFinder


class DummyPos:
    def __init__(self, x: int, y: int, z: int):
        self.x = x
        self.y = y
        self.z = z


async def connect_mcp() -> MCPClient:
    config = {
        "mcpServers": {
            "maicraft": {
                "command": "npx",
                "args": [
                    "-y",
                    "maicraft@latest",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "25565",
                    "--username",
                    "Mai",
                    "--auth",
                    "offline",
                ],
            }
        }
    }
    client = MCPClient(config)
    ok = await client.connect()
    if not ok:
        raise RuntimeError("无法连接到 MCP 服务器，请确保服务器/局域网世界已开启并安装 maicraft")
    return client


async def run_interactive():
    client = await connect_mcp()
    try:
        rf = RecipeFinder(client)

        while True:
            # 使用 EnvironmentUpdater 获取背包与方块缓存（每轮刷新一次）
            updater = EnvironmentUpdater(mcp_client=client, block_cache_viewer=None, update_interval=1)
            await updater.perform_update()
            inventory: List[Any] = global_environment.inventory or []
            block_pos = global_environment.block_position
            if not inventory:
                print("未能从服务器获取到背包，将使用空背包。你也可以手动编辑脚本提供默认背包以测试。")

            item = input("请输入要合成的物品名称 (输入 q 退出，或输入 'recipe 物品名' 查询配方): ").strip()
            if item.lower() in ["q", "quit", "exit"]:
                print("退出测试但保留连接，按 Ctrl+C 可手动断开进程。")
                break
            # 支持现场查询配方
            if item.lower().startswith("recipe ") or item.lower().startswith("r "):
                query_item = item.split(" ", 1)[1].strip()
                print(f"\n[IntegrationTest] 查询 {query_item} 的合成表...\n")
                recipe_text = await rf.find_recipe(query_item)
                print(recipe_text)
                continue
            try:
                count = int(input("请输入合成数量 (默认1): ").strip() or "1")
            except ValueError:
                count = 1

            # 优先使用环境中的坐标，支持手动覆盖
            if block_pos is not None:
                default_x, default_y, default_z = block_pos.x, block_pos.y, block_pos.z
            else:
                default_x, default_y, default_z = 0.0, 64.0, 0.0
            try:
                x = float(input(f"请输入当前位置X (默认{default_x}): ").strip() or str(default_x))
                y = float(input(f"请输入当前位置Y (默认{default_y}): ").strip() or str(default_y))
                z = float(input(f"请输入当前位置Z (默认{default_z}): ").strip() or str(default_z))
            except ValueError:
                x, y, z = default_x, default_y, default_z

            has_table = input("是否模拟附近10格有工作台? (y/n, 默认按环境检测): ").strip().lower()
            if has_table in ["y", "yes", "是", "n", "no", "否"]:
                global_block_cache.clear_cache()
                if has_table in ["y", "yes", "是"]:
                    global_block_cache.add_block("crafting_table", BlockPosition({"x": int(x)+1, "y": int(y), "z": int(z)}))

            ok, summary = await rf.craft_item_smart(item, count, inventory, block_pos or DummyPos(x, y, z))
            print("\n[IntegrationTest] 智能合成结果:\n", summary)

            # 合成后刷新环境并打印可读背包
            await updater.perform_update()
            current_inv = global_environment.inventory or []
            # 可读格式
            if current_inv:
                print("\n[Inventory] 当前物品栏：")
                sorted_inv = sorted(current_inv, key=lambda it: it.get('slot', 0) if isinstance(it, dict) else 0)
                for it in sorted_inv:
                    if isinstance(it, dict):
                        name = it.get('name', '')
                        count_val = it.get('count', 0)
                        print(f"  - {name} x{count_val}")
                    else:
                        print(f"  - {str(it)}")
            else:
                print("\n[Inventory] 物品栏为空")

    finally:
        # 不自动断开，以便继续观察或再次运行。由用户手动终止脚本结束连接。
        pass


if __name__ == "__main__":
    asyncio.run(run_interactive())


