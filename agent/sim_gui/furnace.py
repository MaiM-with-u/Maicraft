from agent.prompt_manager.prompt_manager import prompt_manager
from openai_client.llm_request import LLMClient
from agent.utils.utils import parse_thinking
from agent.common.basic_class import BlockPosition
from agent.block_cache.block_cache import global_block_cache
from agent.action.view_container import view_container
from mcp_server.client import global_mcp_client
from agent.utils.utils import parse_tool_result
from typing import Dict, List, Any
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
            # 添加到全局容器缓存，包含详细的槽位信息
            furnace_inventory = {}
            for slot_items in [self.input_slot, self.fuel_slot, self.output_slot]:
                for item, count in slot_items.items():
                    furnace_inventory[item] = furnace_inventory.get(item, 0) + count
            
            # 创建熔炉槽位信息
            furnace_slots = {
                "input": self.input_slot,
                "fuel": self.fuel_slot,
                "output": self.output_slot
            }
            
            global_container_cache.add_container(self.position, "furnace", furnace_inventory, furnace_slots)
        except Exception:
            # 即使读取失败，也不阻塞后续流程
            self.input_slot = {}
            self.fuel_slot = {}
            self.output_slot = {}

        await global_environment_updater.perform_update()
        input_data = await global_environment.get_all_data()
        result_content = await view_container(self.position.x, self.position.y, self.position.z, self.block.block_type)
        input_data["furnace_gui"] = result_content
        
        # 更新当前熔炉槽位内容
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
            
            # 创建熔炉槽位信息
            furnace_slots = {
                "input": self.input_slot,
                "fuel": self.fuel_slot,
                "output": self.output_slot
            }
            
            global_container_cache.update_container_inventory(self.position, furnace_inventory, furnace_slots)
        except Exception:
            pass

        prompt = prompt_manager.generate_prompt("furnace_gui", **input_data)
        thinking = await self.llm_client.simple_chat(prompt)
        
        logger.info(prompt)
        logger.info(f" 思考结果: {thinking}")
        
        # 解析并执行多个熔炉动作
        execution_result = await self._parse_and_execute_furnace_actions(thinking)
        
        # 如果执行失败，返回错误信息
        if not execution_result.get("success", True):
            return execution_result.get("result_str", "熔炉操作失败")
        
        # 返回执行结果
        return execution_result.get("result_str", "熔炉操作完成")

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
    
    async def _parse_and_execute_furnace_actions(self, thinking: str) -> Dict[str, Any]:
        """
        解析并执行熔炉动作，支持多个动作，失败时终止执行
        返回: {
            "success": bool,  # 是否全部成功
            "executed_actions": List[Dict],  # 已执行的动作列表
            "failed_action": Dict,  # 失败的动作信息
            "error_message": str,  # 错误信息
            "has_exit_action": bool,  # 是否包含退出动作
            "result_str": str  # 结果描述
        }
        """
        import asyncio
        import json
        from json_repair import repair_json
        
        # 匹配所有JSON对象（支持嵌套大括号）
        def find_all_json_objects(text):
            json_objects = []
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
                            json_str = text[start:i+1]
                            json_objects.append((json_str, start, i+1))
                            start = None
            
            return json_objects
        
        # 查找所有JSON对象
        json_objects = find_all_json_objects(thinking)
        furnace_actions = []
        executed_actions = []
        failed_action = None
        error_message = ""
        success = True
        
        # 解析所有熔炉动作
        for json_str, start, end in json_objects:
            try:
                repaired_json = repair_json(json_str)
                json_obj = json.loads(repaired_json)
                action_type = json_obj.get("action_type")
                
                if action_type in ["take_items", "put_items"]:
                    furnace_actions.append(json_obj)
                        
            except Exception as e:
                logger.error(f"[Furnace] 解析动作JSON时异常: {json_str}, 错误: {e}")
                success = False
                error_message = f"解析动作JSON失败: {e}"
                failed_action = {"raw_json": json_str, "parse_error": str(e)}
                break
        
        # 按顺序执行动作
        if furnace_actions and success:
            logger.info(f"[Furnace] 发现 {len(furnace_actions)} 个熔炉动作，开始执行...")
            
            for i, action in enumerate(furnace_actions):
                try:
                    action_type = action.get("action_type")
                    logger.info(f"[Furnace] 执行第 {i+1} 个 {action_type} 动作: {action}")
                    
                    # 执行动作
                    result = await self._execute_furnace_action(action)
                    
                    # 记录执行结果
                    executed_action = {
                        "action": action,
                        "success": result.get("success", False),
                        "result": result.get("result", ""),
                        "error": result.get("error", "")
                    }
                    executed_actions.append(executed_action)
                    
                    # 记录操作信息到结果列表
                    if action_type == "take_items":
                        item = action.get("item")
                        count = action.get("count")
                        slot = action.get("slot")
                        if result.get("success"):
                            action_detail = f"从{slot}槽位取出{item} x{count}成功"
                        else:
                            action_detail = f"从{slot}槽位取出{item} x{count}失败: {result.get('error')}"
                    elif action_type == "put_items":
                        item = action.get("item")
                        count = action.get("count")
                        slot = action.get("slot")
                        if result.get("success"):
                            action_detail = f"向{slot}槽位放入{item} x{count}成功"
                        else:
                            action_detail = f"向{slot}槽位放入{item} x{count}失败: {result.get('error')}"
                    else:
                        action_detail = f"执行{action_type}动作"
                    
                    # 将操作详情添加到执行结果中
                    executed_action["detail"] = action_detail
                    
                    # 如果执行失败，终止后续动作
                    if not result.get("success", False):
                        success = False
                        failed_action = executed_action
                        error_message = result.get("error", "未知错误")
                        logger.error(f"[Furnace] 第 {i+1} 个动作执行失败，终止后续动作")
                        break
                    
                    # 等待 0.3 秒（除了最后一个动作）
                    if i < len(furnace_actions) - 1:
                        await asyncio.sleep(0.3)
                        
                except Exception as e:
                    logger.error(f"[Furnace] 执行第 {i+1} 个熔炉动作时异常: {e}")
                    success = False
                    failed_action = {
                        "action": action,
                        "exception": str(e)
                    }
                    error_message = f"执行动作时发生异常: {e}"
                    break
        
        # 构建结果字符串
        result_parts = []
        if executed_actions:
            
            # 添加每个操作的详细信息
            for action in executed_actions:
                if action.get("detail"):
                    result_parts.append(action["detail"])
            
            if not success:
                result_parts.append(f"执行失败: {error_message}")
        
        return {
            "success": success,
            "executed_actions": executed_actions,
            "failed_action": failed_action,
            "error_message": error_message,
            "result_str": "；".join(result_parts) if result_parts else "没有执行任何动作"
        }
    
    async def _execute_furnace_action(self, action_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行单个熔炉动作
        返回: {
            "success": bool,
            "result": str,
            "error": str
        }
        """
        args = {"x": self.position.x, "y": self.position.y, "z": self.position.z}
        action_type = action_json.get("action_type")
        
        try:
            if action_type == "take_items":
                slot = action_json.get("slot")
                item = action_json.get("item")
                count = action_json.get("count")
                
                if not all([slot, item, count]):
                    return {
                        "success": False,
                        "result": "",
                        "error": f"取出动作参数不完整: slot={slot}, item={item}, count={count}"
                    }
                
                args["items"] = [{"name": item, "count": count, "position": slot}]
                args["action"] = "take"
                
            elif action_type == "put_items":
                slot = action_json.get("slot")
                item = action_json.get("item")
                count = action_json.get("count")
                
                if not all([slot, item, count]):
                    return {
                        "success": False,
                        "result": "",
                        "error": f"放入动作参数不完整: slot={slot}, item={item}, count={count}"
                    }
                
                args["items"] = [{"name": item, "count": count, "position": slot}]
                args["action"] = "put"
                
            else:
                return {
                    "success": False,
                    "result": "",
                    "error": f"不支持的动作类型: {action_type}"
                }
            
            # 调用MCP工具
            call_result = await global_mcp_client.call_tool_directly("use_furnace", args)
            is_success, result_content = parse_tool_result(call_result)
            
            if is_success:
                return {
                    "success": True,
                    "result": result_content,
                    "error": ""
                }
            else:
                return {
                    "success": False,
                    "result": "",
                    "error": result_content
                }
                
        except Exception as e:
            logger.error(f"[Furnace] 执行动作时发生异常: {e}")
            return {
                "success": False,
                "result": "",
                "error": f"执行异常: {e}"
            }