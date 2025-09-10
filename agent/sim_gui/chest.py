from agent.prompt_manager.prompt_manager import prompt_manager
from openai_client.llm_request import LLMClient
from agent.common.basic_class import BlockPosition
from agent.block_cache.block_cache import global_block_cache
from agent.action.view_container import view_container
from mcp_server.client import global_mcp_client
from agent.utils.utils import parse_tool_result, parse_json
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
        self.upper_block = global_block_cache.get_block(position.x, position.y+1, position.z)
        
        # 运行时维护：当前箱子物品与初始化时的快照
        self.chest_inventory: Dict[str, int] = {}
        self.temp_chest_inventory: Dict[str, int] = {}
        
    
    async def chest_gui(self):
        await global_environment_updater.perform_update()
        input_data = await global_environment.get_all_data()
        
        if self.upper_block.block_type != "air" or self.upper_block.block_type != "cave_air":
            return f"位置{self.position.x},{self.position.y},{self.position.z}上方存在方块，箱子无法打开，请移除({self.upper_block.block_type},x = {self.upper_block.x},y = {self.upper_block.y},z = {self.upper_block.z})"

        if self.block.block_type != "chest":
            return f"位置{self.position.x},{self.position.y},{self.position.z}不是箱子"
        
        # 初始化：读取一次原始箱子内容，建立两份快照

        init_inv = await self._get_raw_chest_inventory()
        self.chest_inventory = dict(init_inv)
        self.temp_chest_inventory = dict(init_inv)
        # logger.info(f"[Chest] 初始箱子内容: {init_inv}")
        global_container_cache.add_container(self.position, "chest", init_inv)


        result_content = await view_container(self.position.x, self.position.y, self.position.z, self.block.block_type)
        input_data["chest_gui"] = result_content

        prompt = prompt_manager.generate_prompt("chest_gui", **input_data)
        thinking = await self.llm_client.simple_chat(prompt)
        
        logger.info(f"箱子提示词: {prompt}")
        logger.info(f"箱子思考结果: {thinking}")
        
        # 解析并执行所有动作（包括单个和多个）
        take_items_success, take_items_actions, take_items_log, error_msg = await self.parse_take_items_actions(thinking, self._execute_chest_action)
        
        if take_items_actions:
            final_inv = await self._get_raw_chest_inventory()
            # logger.info(f"[Chest] 最终箱子内容: {final_inv}")
            logger.info(f"[Chest] 对比 - 初始: {self.temp_chest_inventory}, 最终: {final_inv}")
            self.chest_inventory = final_inv
            # 更新全局容器缓存中的库存信息
            global_container_cache.update_container_inventory(self.position, self.chest_inventory)
            # logger.info(f" 执行了 {len(take_items_actions)} 个动作")
            if take_items_success:
                return self._summarize_chest_diff()
            else:
                summary_str = self._summarize_chest_diff()
                return f"箱子使用失败：{error_msg}，{summary_str}"
        else:
            logger.info(f"箱子x{self.position.x},y{self.position.y},z{self.position.z}没有动作")
            return f"箱子x{self.position.x},y{self.position.y},z{self.position.z}没有动作"
            


    async def _execute_chest_action(self, action_json) -> tuple[bool,str]:
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
            if is_success:
                translated_result = translate_use_chest_tool_result(result_content)
            else:
                if "箱子中没有" in str(result_content):
                    translated_result = f"箱子中的{item}数量不足，无法取出{count}个"
                else:
                    translated_result = str(result_content)
            
            return is_success,translated_result
        elif action_type == "put_items":
            item = action_json.get("item")
            count = action_json.get("count")
            
            args["items"] = [{"name": item, "count": count}]
            args["action"] = "store"
            
            call_result = await global_mcp_client.call_tool_directly("use_chest", args)
            is_success, result_content = parse_tool_result(call_result) 
            if is_success:
                translated_result = translate_use_chest_tool_result(result_content)
            else:
                if "物品栏中没有" in str(result_content):
                    translated_result = f"物品栏中的{item}数量不足，无法放入{count}个"
                else:
                    translated_result = str(result_content)
            
            return is_success,translated_result

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

        logger.info(f"[Chest] 计算差异 - prev: {prev}, curr: {curr}")

        # 计算差异：正数表示新增（存入），负数表示减少（取出）
        all_items = set(prev.keys()) | set(curr.keys())
        put_list = []
        take_list = []
        remain_list = []

        for name in sorted(all_items):
            before = prev.get(name, 0)
            after = curr.get(name, 0)
            delta = after - before
            logger.info(f"[Chest] 物品 {name}: before={before}, after={after}, delta={delta}")
            if delta > 0:
                put_list.append(f"{name} x{delta}")
            elif delta < 0:
                take_list.append(f"{name} x{-delta}")
            if after > 0:
                remain_list.append(f"{name} x{after}")

        logger.info(f"[Chest] 计算结果 - put_list: {put_list}, take_list: {take_list}")

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
    
    
    async def parse_take_items_actions(self,thinking: str, execute_action_func) -> tuple[bool, str, list, str, str]:
        """
        解析思考结果中的存取动作 (take_items 和 put_items)
        1. 识别所有符合存取动作格式的 JSON 对象
        2. 按顺序执行这些动作，每个动作间等待 0.3 秒
        3. 返回: (是否成功, 思考结果, 存取动作列表, 非JSON内容)
        """
        import asyncio
        error_msg = ""
        
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
        chest_actions = []
        non_json_content = thinking
        success = True
        
        # 处理每个JSON对象
        for json_str, start, end in json_objects:
            try:
                json_obj = parse_json(json_str)
                if json_obj and json_obj.get("action_type") in ["take_items", "put_items"]:
                    chest_actions.append(json_obj)
                    # 从非JSON内容中移除这个JSON
                    non_json_content = non_json_content.replace(json_str, "").strip()
            except Exception as e:
                logger.error(f"[Utils] 解析存取动作 JSON时异常: {json_str}, 错误: {e}")
                success = False
        
        # 清理非JSON内容
        non_json_content = non_json_content.replace("```json", "").replace("```", "").strip()
        
        # 按顺序执行所有存取动作
        if chest_actions and execute_action_func:
            
            for i, action in enumerate(chest_actions):
                try:
                    action_success,result = await execute_action_func(action)
                    logger.info(f"第 {i+1} 个动作执行结果: {result.result_str if hasattr(result, 'result_str') else str(result)}")
                    
                    if not action_success:
                        return False, chest_actions, non_json_content, result
                    
                    # 等待 0.3 秒（除了最后一个动作）
                    if i < len(chest_actions) - 1:
                        await asyncio.sleep(0.3)
                        
                except Exception as e:
                    logger.error(f"[Utils] 执行第 {i+1} 个存取动作时异常: {e}")
                    success = False
        
        return success, chest_actions, non_json_content, error_msg