from agent.prompt_manager.prompt_manager import prompt_manager
from openai_client.llm_request import LLMClient
from agent.utils.utils import parse_take_items_actions
from agent.environment.basic_info import BlockPosition
from agent.block_cache.block_cache import global_block_cache
from agent.action.view_container import view_container
from mcp_server.client import global_mcp_client
from agent.utils.utils import parse_tool_result
from agent.utils.utils_tool_translation import translate_use_chest_tool_result
from typing import Dict
from agent.environment.environment import global_environment
from agent.environment.environment_updater import global_environment_updater
from agent.container_cache.container_cache import global_container_cache
from utils.logger import get_logger

logger = get_logger("ChestSimGui")


class ChestSimGui:
    def __init__(self,position:BlockPosition,llm_client:LLMClient):
        self.llm_client = llm_client
        self.position = position
        self.block = global_block_cache.get_block(position.x, position.y, position.z)

        self.lasting_time = 10
        
        # 运行时维护：当前箱子物品与初始化时的快照
        self.chest_inventory: Dict[str, int] = {}
        self.temp_chest_inventory: Dict[str, int] = {}
        
    
    async def chest_gui(self):
        await global_environment_updater.perform_update()
        input_data = await global_environment.get_all_data()
        
        if self.block.block_type != "chest":
            return f"位置{self.position.x},{self.position.y},{self.position.z}不是箱子"
        
        # 初始化：读取一次原始箱子内容，建立两份快照
        try:
            init_inv = await self._get_raw_chest_inventory()
            self.chest_inventory = dict(init_inv)
            self.temp_chest_inventory = dict(init_inv)
            # 添加到全局容器缓存
            global_container_cache.add_container(self.position, "chest", init_inv)
        except Exception:
            # 即使读取失败，也不阻塞后续流程
            self.chest_inventory = {}
            self.temp_chest_inventory = {}


        result_content = await view_container(self.position.x, self.position.y, self.position.z, self.block.block_type)
        input_data["chest_gui"] = result_content

        prompt = prompt_manager.generate_prompt("chest_gui", **input_data)
        thinking = await self.llm_client.simple_chat(prompt)
        
        logger.info(f"箱子提示词: {prompt}")
        logger.info(f"箱子思考结果: {thinking}")
        
        # 解析并执行所有动作（包括单个和多个）
        take_items_success, take_items_thinking, take_items_actions, take_items_log = await parse_take_items_actions(thinking, self._execute_chest_action)
        
        if take_items_actions:
            self.chest_inventory = await self._get_raw_chest_inventory()
            # 更新全局容器缓存中的库存信息
            global_container_cache.update_container_inventory(self.position, self.chest_inventory)
            logger.info(f" 执行了 {len(take_items_actions)} 个动作")
            return self._summarize_chest_diff()
        else:
            logger.info(f"箱子x{self.position.x},y{self.position.y},z{self.position.z}没有动作")
            return f"箱子x{self.position.x},y{self.position.y},z{self.position.z}没有动作"
            


    async def _execute_chest_action(self, action_json) -> str:
        """执行单个箱子动作"""
        args = {"x": self.position.x, "y": self.position.y, "z": self.position.z}
        action_type = action_json.get("action_type")
        
        if action_type == "take_items":
            item = action_json.get("item")
            count = action_json.get("count")
            
            args["items"] = [{"name": item, "count": count}]
            args["action"] = "withdraw"
            
            call_result = await global_mcp_client.call_tool_directly("use_chest", args)
            is_success, result_content = parse_tool_result(call_result) 
            translated_result = translate_use_chest_tool_result(result_content)
            
            return translated_result
        elif action_type == "put_items":
            item = action_json.get("item")
            count = action_json.get("count")
            
            args["items"] = [{"name": item, "count": count}]
            args["action"] = "store"
            
            call_result = await global_mcp_client.call_tool_directly("use_chest", args)
            is_success, result_content = parse_tool_result(call_result) 
            translated_result = translate_use_chest_tool_result(result_content)
            
            return translated_result

    async def _get_raw_chest_inventory(self) -> Dict[str, int]:
        """查询箱子原始内容，返回 {物品名: 数量} 的字典。"""
        args = {"x": self.position.x, "y": self.position.y, "z": self.position.z, "includeContainerInfo": True}
        call_result = await global_mcp_client.call_tool_directly("query_block", args)
        is_success, result_content = parse_tool_result(call_result)
        if not is_success:
            return {}
        # 兼容完整响应或data层
        data_obj = result_content.get("data", result_content) if isinstance(result_content, dict) else {}
        container_info = data_obj.get("containerInfo", {}) if isinstance(data_obj, dict) else {}
        slots = container_info.get("slots", []) if isinstance(container_info, dict) else []
        inventory: Dict[str, int] = {}
        for slot in slots:
            try:
                name = slot.get("name")
                count = slot.get("count", 0)
                if not name or name == "air" or count <= 0:
                    continue
                inventory[name] = inventory.get(name, 0) + int(count)
            except Exception:
                continue
        return inventory

    def _summarize_chest_diff(self) -> str:
        """对比 temp 与当前 chest_inventory，输出存入/取出/剩余摘要。"""
        prev = self.temp_chest_inventory or {}
        curr = self.chest_inventory or {}

        # 计算差异：正数表示新增（存入），负数表示减少（取出）
        all_items = set(prev.keys()) | set(curr.keys())
        put_list = []
        take_list = []
        remain_list = []

        for name in sorted(all_items):
            before = prev.get(name, 0)
            after = curr.get(name, 0)
            delta = after - before
            if delta > 0:
                put_list.append(f"{name} x{delta}")
            elif delta < 0:
                take_list.append(f"{name} x{-delta}")
            if after > 0:
                remain_list.append(f"{name} x{after}")

        lines = [""]
        if put_list:
            lines.append("存入: " + "，".join(put_list))
        else:
            lines.append("存入: 无")
        if take_list:
            lines.append("取出: " + "，".join(take_list))
        else:
            lines.append("取出: 无")
        # if remain_list:
        #     lines.append("箱内剩余: " + "，".join(remain_list))
        # else:
        #     lines.append("箱内剩余: 空")

        return "\n".join(lines)