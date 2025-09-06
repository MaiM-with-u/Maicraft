from agent.prompt_manager.prompt_manager import prompt_manager
from openai_client.llm_request import LLMClient
from agent.utils.utils import parse_thinking
from agent.environment.basic_info import BlockPosition
from agent.block_cache.block_cache import global_block_cache
from agent.action.view_container import view_container
from mcp_server.client import global_mcp_client
from agent.utils.utils import parse_tool_result
from typing import Dict, List
from agent.environment.environment import global_environment
from agent.environment.environment_updater import global_environment_updater
from utils.logger import get_logger
from agent.thinking_log import global_thinking_log
from agent.container_cache.container_cache import global_container_cache

logger = get_logger("FurnaceSimGui")

class FurnaceSimGui:
    def __init__(self,position:BlockPosition,llm_client:LLMClient):
        self.llm_client = llm_client
        self.position = position
        self.block = global_block_cache.get_block(position.x, position.y, position.z)

        self.lasting_time = 10
        
        # 熔炉三个槽位的缓存：{物品名: 数量}
        self.input_slot: Dict[str, int] = {}
        self.fuel_slot: Dict[str, int] = {}
        self.output_slot: Dict[str, int] = {}
        
    
    async def furnace_gui(self):
        await global_environment_updater.perform_update()
        input_data = await global_environment.get_all_data()
        
        if not self.block:
            return f"位置{self.position.x},{self.position.y},{self.position.z}不存在方块，无法查看"
        
        if self.block.block_type not in ["furnace", "blast_furnace", "smoker"]:
            return f"位置{self.position.x},{self.position.y},{self.position.z}不是熔炉，无法查看{self.block.block_type}"
        
        # 初始化：读取一次原始熔炉内容，建立三个槽位的快照
        try:
            init_slots = await self._get_raw_furnace_slots()
            self.input_slot = dict(init_slots.get("input", {}))
            self.fuel_slot = dict(init_slots.get("fuel", {}))
            self.output_slot = dict(init_slots.get("output", {}))
            # 添加到全局容器缓存，合并所有槽位的物品
            furnace_inventory = {}
            for slot_items in [self.input_slot, self.fuel_slot, self.output_slot]:
                for item, count in slot_items.items():
                    furnace_inventory[item] = furnace_inventory.get(item, 0) + count
            global_container_cache.add_container(self.position, "furnace", furnace_inventory)
        except Exception:
            # 即使读取失败，也不阻塞后续流程
            self.input_slot = {}
            self.fuel_slot = {}
            self.output_slot = {}

        while True:
            await global_environment_updater.perform_update()
            input_data = await global_environment.get_all_data()
            result_content = await view_container(self.position.x, self.position.y, self.position.z, self.block.block_type)
            input_data["furnace_gui"] = result_content
            
            # 每次循环更新当前熔炉槽位内容
            try:
                current_slots = await self._get_raw_furnace_slots()
                self.input_slot = dict(current_slots.get("input", {}))
                self.fuel_slot = dict(current_slots.get("fuel", {}))
                self.output_slot = dict(current_slots.get("output", {}))
                # 更新全局容器缓存
                furnace_inventory = {}
                for slot_items in [self.input_slot, self.fuel_slot, self.output_slot]:
                    for item, count in slot_items.items():
                        furnace_inventory[item] = furnace_inventory.get(item, 0) + count
                global_container_cache.update_container_inventory(self.position, furnace_inventory)
            except Exception:
                pass

            prompt = prompt_manager.generate_prompt("furnace_gui", **input_data)
            thinking = await self.llm_client.simple_chat(prompt)
            success, thinking, json_obj, thinking_log = parse_thinking(thinking)
            
            logger.info(prompt)
            logger.info(f" 思考结果: {thinking}")
            
            args = {"x": self.position.x, "y": self.position.y, "z": self.position.z}
            action_type = json_obj.get("action_type")
            
            if action_type == "take_items":
                slot = json_obj.get("slot")
                item = json_obj.get("item")
                count = json_obj.get("count")
                
                
                args["items"] = [{"name": item, "count": count, "position": slot}]
                args["action"] = "take"
                
                call_result = await global_mcp_client.call_tool_directly("use_furnace", args)
                is_success, result_content = parse_tool_result(call_result) 
                # 记录操作
                if not is_success:
                    global_thinking_log.add_thinking_log(f"取出{item} x{count}失败: {result_content}","action")
                    
                else:
                    global_thinking_log.add_thinking_log(f"取出{item} x{count}成功: {result_content}","action")
                
            elif action_type == "put_items":
                slot = json_obj.get("slot")
                item = json_obj.get("item")
                count = json_obj.get("count")
                
                args["items"] = [{"name": item, "count": count, "position": slot}]
                args["action"] = "put"
                
                call_result = await global_mcp_client.call_tool_directly("use_furnace", args)
                is_success, result_content = parse_tool_result(call_result) 
                # 记录操作
                if not is_success:
                    global_thinking_log.add_thinking_log(f"放入{item} x{count}失败: {result_content}")
                    
                else:
                    global_thinking_log.add_thinking_log(f"放入{item} x{count}成功: {result_content}")
                    
                
            elif action_type == "exit_furnace_gui":
                return "关闭熔炼界面"
            else:
                return f"不支持的动作类型: {action_type}"

    async def _get_raw_furnace_slots(self) -> Dict[str, Dict[str, int]]:
        """查询熔炉原始内容，返回 {槽位名: {物品名: 数量}} 的字典。"""
        args = {"x": self.position.x, "y": self.position.y, "z": self.position.z, "includeContainerInfo": True}
        call_result = await global_mcp_client.call_tool_directly("query_block", args)
        is_success, result_content = parse_tool_result(call_result)
        if not is_success:
            return {"input": {}, "fuel": {}, "output": {}}
        
        # 兼容完整响应或data层
        data_obj = result_content.get("data", result_content) if isinstance(result_content, dict) else {}
        container_info = data_obj.get("containerInfo", {}) if isinstance(data_obj, dict) else {}
        slots = container_info.get("slots", []) if isinstance(container_info, dict) else []
        
        # 槽位映射：0=input, 1=fuel, 2=output
        slot_names = {0: "input", 1: "fuel", 2: "output"}
        furnace_slots = {"input": {}, "fuel": {}, "output": {}}
        
        for slot in slots:
            try:
                slot_num = slot.get("slot", 0)
                slot_name = slot_names.get(slot_num, "unknown")
                if slot_name == "unknown":
                    continue
                    
                name = slot.get("name")
                count = slot.get("count", 0)
                if not name or name == "air" or count <= 0:
                    continue
                    
                if name not in furnace_slots[slot_name]:
                    furnace_slots[slot_name][name] = 0
                furnace_slots[slot_name][name] += int(count)
            except Exception:
                continue
                
        return furnace_slots