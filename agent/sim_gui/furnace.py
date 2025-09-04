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
        
        # 操作记录：记录每次放入/取出的操作
        self.use_record: List[Dict] = []
        
    
    async def furnace_gui(self):
        await global_environment_updater.perform_update()
        input_data = await global_environment.get_all_data()
        
        if self.block.block_type not in ["furnace", "blast_furnace", "smoker"]:
            return f"位置{self.position.x},{self.position.y},{self.position.z}不是熔炉，无法查看{self.block.block_type}"
        
        # 初始化：读取一次原始熔炉内容，建立三个槽位的快照
        try:
            init_slots = await self._get_raw_furnace_slots()
            self.input_slot = dict(init_slots.get("input", {}))
            self.fuel_slot = dict(init_slots.get("fuel", {}))
            self.output_slot = dict(init_slots.get("output", {}))
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
            except Exception:
                pass

            prompt = prompt_manager.generate_prompt("furnace_gui", **input_data)
            thinking = await self.llm_client.simple_chat(prompt)
            success, thinking, json_obj, thinking_log = parse_thinking(thinking)
            
            args = {"x": self.position.x, "y": self.position.y, "z": self.position.z}
            action_type = json_obj.get("action_type")
            
            if action_type == "take_items":
                slot = json_obj.get("slot")
                item = json_obj.get("item")
                count = json_obj.get("count")
                
                
                args["items"] = [{"name": item, "count": count}]
                args["action"] = "withdraw"
                args["slot"] = slot
                
                call_result = await global_mcp_client.call_tool_directly("use_furnace", args)
                is_success, result_content = parse_tool_result(call_result) 
                # 记录操作
                self.use_record.append({
                    "action": "取出",
                    "slot": slot,
                    "item": item,
                    "count": count,
                    "success": is_success
                })
                
                
            elif action_type == "put_items":
                slot = json_obj.get("slot")
                item = json_obj.get("item")
                count = json_obj.get("count")
                
                args["items"] = [{"name": item, "count": count}]
                args["action"] = "store"
                args["slot"] = slot
                
                call_result = await global_mcp_client.call_tool_directly("use_furnace", args)
                is_success, result_content = parse_tool_result(call_result) 
                # 记录操作
                self.use_record.append({
                    "action": "放入",
                    "slot": slot,
                    "item": item,
                    "count": count,
                    "success": is_success
                })

                
            elif action_type == "exit_furnace_gui":
                # 循环结束前做一次最终同步
                try:
                    final_slots = await self._get_raw_furnace_slots()
                    self.input_slot = dict(final_slots.get("input", {}))
                    self.fuel_slot = dict(final_slots.get("fuel", {}))
                    self.output_slot = dict(final_slots.get("output", {}))
                except Exception:
                    pass
                return self._summarize_furnace_operations()
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

    def _summarize_furnace_operations(self) -> str:
        """输出熔炉操作记录和当前物品情况。"""
        lines = ["退出熔炉界面"]
        
        # 1. 操作记录
        if self.use_record:
            lines.append("\n操作记录:")
            for i, record in enumerate(self.use_record, 1):
                action = record.get("action", "")
                slot = record.get("slot", "")
                item = record.get("item", "")
                count = record.get("count", 0)
                success = record.get("success", False)
                if not success:
                    lines.append(f"  {i}. {action} {slot}槽位: {item} x{count} 失败")
                    continue
                lines.append(f"  {i}. {action} {slot}槽位: {item} x{count} 成功")
        else:
            lines.append("\n操作记录: 无")
        
        # 2. 熔炉现在的物品情况
        lines.append("\n熔炉当前物品情况:")
        
        # 输入槽位
        if self.input_slot:
            input_items = [f"{name} x{count}" for name, count in self.input_slot.items()]
            lines.append(f"  输入槽位: {', '.join(input_items)}")
        else:
            lines.append("  输入槽位: 空")
            
        # 燃料槽位
        if self.fuel_slot:
            fuel_items = [f"{name} x{count}" for name, count in self.fuel_slot.items()]
            lines.append(f"  燃料槽位: {', '.join(fuel_items)}")
        else:
            lines.append("  燃料槽位: 空")
            
        # 输出槽位
        if self.output_slot:
            output_items = [f"{name} x{count}" for name, count in self.output_slot.items()]
            lines.append(f"  输出槽位: {', '.join(output_items)}")
        else:
            lines.append("  输出槽位: 空")

        return "\n".join(lines)