import asyncio
import time
import math
from typing import List, Any, Optional
from langchain_core.tools import BaseTool
from utils.logger import get_logger
from config import global_config
from openai_client.llm_request import LLMClient
from openai_client.modelconfig import ModelConfig
from agent.environment.environment_updater import EnvironmentUpdater
from agent.environment.environment import global_environment
from agent.prompt_manager.prompt_manager import prompt_manager
from agent.block_cache.block_cache import global_block_cache
from agent.prompt_manager.template import init_templates
from agent.utils.utils import (
    parse_json, convert_mcp_tools_to_openai_format, parse_tool_result, filter_action_tools,
    parse_thinking,
)
from agent.to_do_list import ToDoList
from agent.action.craft_action.craft_action import recipe_finder
import traceback
from agent.block_cache.nearby_block import NearbyBlockManager
from view_render.block_cache_viewer import BlockCacheViewer
from agent.action.place_action import PlaceAction
from agent.action.move_action import MoveAction
from agent.utils.utils_tool_translation import (
    translate_move_tool_result, 
    translate_mine_nearby_tool_result, 
    translate_mine_block_tool_result, 
    translate_place_block_tool_result, 
    translate_chat_tool_result,
    translate_start_smelting_tool_result,
    translate_collect_smelted_items_tool_result,
    translate_use_chest_tool_result
)
from agent.action.view_container import ViewContainer
from mcp_server.client import global_mcp_client
from agent.thinking_log import global_thinking_log
from agent.mai_mode import mai_mode

COLOR_MAP = {
    "main_mode": "\033[32m",        # 绿色
    "move_mode": "\033[38;5;141m",  # 橙色
    "mining_mode": "\033[38;5;226m",  # 黄色
    "chat_mode": "\033[38;5;51m",     # 青色
    "memo_mode": "\033[38;5;199m",    # 粉色
    "task_edit_mode": "\033[38;5;196m", # 红色
    "use_block_mode": "\033[38;5;208m", # 紫色（与use_mode相同）
}



class ThinkingJsonResult:
    def __init__(self):
        self.result_str = ""
        self.done = False
        self.new_task = ""
        self.new_task_id = ""
        self.progress = ""
        self.rewrite = ""
        self.task_id = ""
        
        
class TaskResult:
    def __init__(self):
        self.status = "rechoice"
        self.message = ""
        self.result = ""
        self.action = ""
        
        self.new_task_id = ""
        self.rewrite = ""

class MaiAgent:
    def __init__(self):
        self.logger = get_logger("MaiAgent")

        # 初始化LLM客户端
        self.llm_client: Optional[LLMClient] = None
        self.llm_client_fast: Optional[LLMClient] = None
        
        
        self.vlm: Optional[LLMClient] = None
        


        # 初始化LLM和工具适配器
        # 延迟初始化
        self.tools: Optional[List[BaseTool]] = None

        # 环境更新器
        self.environment_updater: Optional[EnvironmentUpdater] = None
        
        # 延迟初始化NearbyBlockManager，确保在EnvironmentUpdater启动后再创建
        self.nearby_block_manager: Optional[NearbyBlockManager] = None

        self.place_action: Optional[PlaceAction] = None
        self.move_action: Optional[MoveAction] = None
        self.view_container: Optional[ViewContainer] = None
        # 初始化状态
        self.initialized = False
        
        
        self.goal_list: list[tuple[str, str, str]] = []  # (goal, status, details)

        self.goal = "进行自由游玩"

        self.memo_list: list[str] = []
        
        self.on_going_task_id = ""
        
        
        self.to_do_list: ToDoList = ToDoList()
        self.task_done_list: list[tuple[bool, str, str]] = []
        
        # 方块缓存预览窗口
        self.block_cache_viewer: Optional[BlockCacheViewer] = None
        self._viewer_started: bool = False
        self.exec_task: Optional[asyncio.Task] = None
        # 不再需要_viewer_task，因为现在使用线程
        
        
    async def initialize(self):
        """异步初始化"""
        try:
            self.logger.info(" 开始初始化")
            
            init_templates()
            
            # 初始化LLM客户端
            model_config = ModelConfig(
                model_name=global_config.llm.model,
                api_key=global_config.llm.api_key,
                base_url=global_config.llm.base_url,
                max_tokens=global_config.llm.max_tokens,
                temperature=global_config.llm.temperature
            )
            
            
            self.llm_client = LLMClient(model_config)
            
            model_config = ModelConfig(
                model_name=global_config.vlm.model,
                api_key=global_config.vlm.api_key,
                base_url=global_config.vlm.base_url,
                max_tokens=global_config.vlm.max_tokens,
                temperature=global_config.vlm.temperature
            )
            
            self.vlm = LLMClient(model_config)
            global_environment.set_vlm(self.vlm)
            
            
            self.logger.info(" LLM客户端初始化成功")
            
            
            self.tools = await global_mcp_client.get_tools_metadata()
            self.action_tools = filter_action_tools(self.tools)
            self.logger.info(f" 获取到 {len(self.action_tools)} 个可用工具")
            self.openai_tools = convert_mcp_tools_to_openai_format(self.action_tools)

            await self._start_block_cache_viewer()
            
            # 创建并启动环境更新器
            self.environment_updater = EnvironmentUpdater(
                mcp_client = global_mcp_client,
                update_interval=0.1,  # 默认5秒更新间隔
            )
            
            self.place_action = PlaceAction()
            self.move_action = MoveAction()
            self.view_container = ViewContainer(global_mcp_client)
            # 启动环境更新器
            if self.environment_updater.start():
                self.logger.info(" 环境更新器启动成功")
            else:
                self.logger.error(" 环境更新器启动失败")

            await asyncio.sleep(1)
            
            # 初始化NearbyBlockManager
            self.nearby_block_manager = NearbyBlockManager()
            self.logger.info(" NearbyBlockManager初始化成功")

            self.initialized = True
            self.logger.info(" 初始化完成")

            # 启动方块缓存预览窗口（后台，不阻塞事件循环）
            
            self.inventory_old:List[Any] = []
            
            

        except Exception as e:
            self.logger.error(f" 初始化失败: {e}")
            raise
                
    async def run_execute_loop(self):
        """
        运行执行循环
        """
        self.on_going_task_id = ""
        mai_mode.mode = "main_mode"
        while True:
            await self.next_thinking()
    
    def _format_task_done_list(self) -> str:
        """将任务执行记录翻译成可读文本，只取最近10条。

        任务记录为 (success: bool, task_id: str, message: str)
        """
        if not self.task_done_list:
            return "暂无任务执行记录"

        lines: list[str] = []
        # 仅取最近10条
        for success, task_id, message in self.task_done_list[-10:]:
            status_text = "成功" if success else "失败"
            # 规避 None/空值
            safe_task_id = str(task_id) if task_id is not None else ""
            safe_message = str(message) if message is not None else ""
            lines.append(f"任务ID {safe_task_id}：{status_text}（{safe_message}）")

        return "\n".join(lines)


    async def next_thinking(self) -> TaskResult:
        """
        执行目标
        返回: (执行结果, 执行状态)
        """
        try:
            
            task = self.to_do_list.get_task_by_id(self.on_going_task_id)
            if task:
                self.logger.info(f"执行任务:\n {task}")
            else:
                self.logger.debug("没有任务")
            
            # 获取当前环境信息
            await self.environment_updater.perform_update()
            environment_info = global_environment.get_summary()
            nearby_block_info = await self.nearby_block_manager.get_block_details_mix_str(global_environment.block_position)

            # 使用原有的提示词模板，但通过call_tool传入工具
            input_data = {
                "task": task.__str__(),
                "environment": environment_info,
                # "executed_tools": executed_tools_str,
                "thinking_list": global_thinking_log.get_thinking_log(),
                "nearby_block_info": nearby_block_info,
                "position": global_environment.get_position_str(),
                "memo_list": "\n".join(self.memo_list),
                "chat_str": global_environment.get_chat_str(),
                "to_do_list": self.to_do_list.__str__(),
                "task_done_list": self._format_task_done_list(),
                "goal": self.goal,
                "mode": mai_mode.mode
            }
            
            # 根据不同的模式，给予不同的工具
            if mai_mode.mode == "main_mode":
                # 主模式，可以选择基础动作，和深入动作
                prompt = prompt_manager.generate_prompt("minecraft_excute_task_thinking", **input_data)
                # self.logger.info(f" 执行任务提示词: {prompt}")
            elif mai_mode.mode == "task_edit":
                prompt = prompt_manager.generate_prompt("minecraft_excute_task_action", **input_data)
                # self.logger.info(f"\033[38;5;153m 执行任务提示词: {prompt}\033[0m")
            elif mai_mode.mode == "move_mode":
                prompt = prompt_manager.generate_prompt("move_mode", **input_data)
                # self.logger.info(f"\033[38;5;208m 执行任务提示词: {prompt}\033[0m")
            elif mai_mode.mode == "use_block":
                prompt = prompt_manager.generate_prompt("use_block_mode", **input_data)
                # self.logger.info(f"\033[38;5;208m 执行任务提示词: {prompt}\033[0m")
            elif mai_mode.mode == "mining_mode":
                prompt = prompt_manager.generate_prompt("minecraft_mining_nearby", **input_data)
                # self.logger.info(f"\033[38;5;208m 执行任务提示词: {prompt}\033[0m")
            elif mai_mode.mode == "memo":
                prompt = prompt_manager.generate_prompt("memo_mode", **input_data)
                # self.logger.info(f"\033[38;5;208m 执行任务提示词: {prompt}\033[0m")
            elif mai_mode.mode == "chat":
                prompt = prompt_manager.generate_prompt("mai_chat", **input_data)
                # self.logger.info(f"\033[38;5;208m 执行任务提示词: {prompt}\033[0m")
            else:
                self.logger.warning(f" 不支持的模式: {mai_mode.mode}")
                return
            
            
            thinking = await self.llm_client.simple_chat(prompt)
            # self.logger.info(f" 原始输出: {thinking}")
            
            json_obj, thinking_log = parse_thinking(thinking)
            
            #出现意外的调试
            if not json_obj:
                self.logger.warning(f" 思考结果中没有json对象: {thinking}")
                return TaskResult()
            
            action_type = json_obj.get("action_type")
            if not action_type:
                self.logger.warning(f" 思考结果中没有action_type: {thinking}")
                return TaskResult()
            
            
            time_str = time.strftime("%H:%M:%S", time.localtime())
            color_prefix = COLOR_MAP.get(mai_mode.mode, "\033[0m")
            
            if thinking_log:
                global_thinking_log.add_thinking_log(f"时间：{time_str} 思考结果：{thinking_log}")
                
            self.logger.info(f"{color_prefix} 想法{mai_mode.mode}: {thinking_log}\033[0m")
            
            if json_obj:
                self.logger.info(f"{color_prefix} 动作: {json_obj}\033[0m")
                
                result = await self.excute_action(json_obj)
                global_thinking_log.add_thinking_log(f"时间：{time_str} 执行结果：{result.result_str}")
                
                self.logger.info(f" 执行结果: {result.result_str}")
                
                
        except Exception as e:
            self.logger.error(f" 任务执行异常: {traceback.format_exc()}")
        
        
        
    async def excute_action(self,action_json) -> ThinkingJsonResult:
        if mai_mode.mode == "main_mode":
            return await self.excute_main_mode(action_json)
        elif mai_mode.mode == "move_mode":
            return await self.excute_move_mode(action_json)
        elif mai_mode.mode == "mining_mode":
            return await self.excute_mining_mode(action_json)
        elif mai_mode.mode == "use_block":
            return await self.excute_use_mode(action_json)
        elif mai_mode.mode == "memo":
            return await self.excute_memo(action_json)
        elif mai_mode.mode == "chat":
            return await self.excute_chat(action_json)
        elif mai_mode.mode == "task_edit":
            return await self.excute_task_edit(action_json)
        else:
            self.logger.warning(f" {mai_mode.mode} 不支持的action_type: {action_json.get('action_type')}")
            return ThinkingJsonResult()
            
            
    async def excute_main_mode(self,action_json) -> ThinkingJsonResult:
        result = ThinkingJsonResult()
        action_type = action_json.get("action_type")
        if action_type == "move":
            position = action_json.get("position", {})
            x = math.floor(float(position.get("x", 0)))
            y = math.floor(float(position.get("y", 0)))
            z = math.floor(float(position.get("z", 0)))
            args = {"x": x, "y": y, "z": z, "type": "coordinate"}
            result.result_str = f"尝试移动到：{x},{y},{z}\n"
            call_result = await global_mcp_client.call_tool_directly("move", args)
            is_success, result_content = parse_tool_result(call_result)
            result.result_str += translate_move_tool_result(result_content, args)
            return result
        elif action_type == "break_block":
            x = math.floor(float(action_json.get("x")))
            y = math.floor(float(action_json.get("y")))
            z = math.floor(float(action_json.get("z")))
            block_cache = global_block_cache.get_block(x, y, z)
            if not block_cache:
                result.result_str += f"位置{x},{y},{z}太远，无法挖掘\n"
                return result
            if block_cache.block_type == "air":
                result.result_str += f"位置{x},{y},{z}不存在方块，无法破坏\n"
                return result
            if block_cache.block_type == "water" or block_cache.block_type == "lava" or block_cache.block_type == "bedrock":
                result.result_str += f"位置{x},{y},{z}是{block_cache.block_type}，无法破坏\n"
                return result
            args = {"x": x, "y": y, "z": z,"digOnly": True}
            result.result_str = f"尝试破坏位置：{x},{y},{z}\n"
            call_result = await global_mcp_client.call_tool_directly("mine_block", args)
            is_success, result_content = parse_tool_result(call_result)
            if is_success:
                result.result_str += translate_mine_block_tool_result(result_content)
            else:
                result.result_str += f"挖掘失败: {result_content}"
        elif action_type == "place_block":
            block = action_json.get("block")
            x = action_json.get("x")
            y = action_json.get("y")
            z = action_json.get("z")
            result_str, args = await self.place_action.place_action(block, x, y, z)            
            result.result_str = result_str
            if not args:
                return result
            call_result = await global_mcp_client.call_tool_directly("place_block", args)
            is_success, result_content = parse_tool_result(call_result)
            result.result_str += translate_place_block_tool_result(result_content,args)
        elif action_type == "enter_move_mode":
            reason = action_json.get("reason")
            mai_mode.mode = "move_mode"
            result.result_str = f"想要移动，进入move模式，原因是: {reason}\n"
            return result
        elif action_type == "enter_mining_mode":
            mai_mode.mode = "mining_mode"
            result.result_str = "进入采矿/采掘模式\n"
            return result
        elif action_type == "enter_use_block_mode":
            reason = action_json.get("reason")
            result.result_str = f"想要使用方块，进入use模式，原因是: {reason}\n"
            mai_mode.mode = "use_block"
            return result
        elif action_type == "enter_memo_mode":
            reason = action_json.get("reason")
            result.result_str = f"想要使用备忘录，进入memo模式，原因是: {reason}\n"
            mai_mode.mode = "memo"
            return result
        elif action_type == "enter_task_edit_mode":
            mai_mode.mode = "task_edit"
            reason = action_json.get("reason")
            result.result_str = f"选择进行修改任务列表: \n原因: {reason}\n"
            return result
        elif action_type == "enter_chat_mode":
            mai_mode.mode = "chat"
            reason = action_json.get("reason")
            result.result_str = f"想要聊天，进入chat模式，原因是: {reason}\n"
            return result
        else:
            self.logger.warning(f" {mai_mode.mode} 不支持的action_type: {action_type}")
            
            
        return result

    async def excute_chat(self,action_json) -> ThinkingJsonResult:
        result = ThinkingJsonResult()
        action_type = action_json.get("action_type")
        if action_type == "chat":
            message = action_json.get("message")
            if message is not None:
                message = message.strip().replace('\n', '').replace('\r', '')
            args = {"message": message}
            call_result = await global_mcp_client.call_tool_directly("chat", args)
            is_success, result_content = parse_tool_result(call_result)
            return result
        elif action_type == "wait_player_message":
            wait_time = action_json.get("wait_time")
            result.result_str = f"等待玩家消息: \n等待时间: {wait_time}\n"
            await asyncio.sleep(wait_time)
            return result
        elif action_type == "exit_chat_mode":
            mai_mode.mode = "main_mode"
            reason = action_json.get("reason")
            result.result_str = f"退出聊天模式: \n原因: {reason}\n"
            return result
        return result
    
    async def excute_move_mode(self,action_json) -> ThinkingJsonResult:
        result = ThinkingJsonResult()
        action_type = action_json.get("action_type")
        if action_type == "move_action":
            position = action_json.get("position", {})
            x = math.floor(float(position.get("x", 0)))
            y = math.floor(float(position.get("y", 0)))
            z = math.floor(float(position.get("z", 0)))
            args = {"x": x, "y": y, "z": z, "type": "coordinate"}
            result.result_str = f"尝试移动到：{x},{y},{z}\n"
            call_result = await global_mcp_client.call_tool_directly("move", args)
            is_success, result_content = parse_tool_result(call_result)
            result.result_str += translate_move_tool_result(result_content, args)
        elif action_type == "exit_move_mode":
            mai_mode.mode = "main_mode"
            reason = action_json.get("reason")
            result.result_str = f"退出移动模式: \n原因: {reason}\n"
            return result
        else:
            self.logger.warning(f" {mai_mode.mode} 不支持的action_type: {action_type}")
            result.result_str = f"当前模式{mai_mode.mode}不支持的action_type: {action_type}\n"
        
        return result
    
    async def excute_mining_mode(self,action_json) -> ThinkingJsonResult:
        result = ThinkingJsonResult()
        action_type = action_json.get("action_type")
        if action_type == "mine_nearby":
            name = action_json.get("name")
            count = action_json.get("count")
            result.result_str = f"想要批量挖掘: {name} 数量: {count}\n"
            args = {"name": name, "count": count}
            call_result = await global_mcp_client.call_tool_directly("mine_block", args)
            is_success, result_content = parse_tool_result(call_result)
            if is_success:
                result.result_str += translate_mine_nearby_tool_result(result_content)
            else:
                result.result_str += f"批量挖掘失败: {result_content}"
        elif action_type == "mine_block":
            positions = action_json.get("position")
            for position in positions:
                x = math.floor(float(position.get("x")))
                y = math.floor(float(position.get("y")))
                z = math.floor(float(position.get("z")))
                block_cache = global_block_cache.get_block(x, y, z)
                if not block_cache:
                    result.result_str += f"位置{x},{y},{z}不存在方块，无法挖掘\n"
                    return result
                if block_cache.block_type == "air":
                    result.result_str += f"位置{x},{y},{z}不存在方块，无法挖掘\n"
                    return result
                if block_cache.block_type == "water" or block_cache.block_type == "lava" or block_cache.block_type == "bedrock":
                    result.result_str += f"位置{x},{y},{z}是{block_cache.block_type}，无法挖掘\n"
                    return result
                
                args = {"x": x, "y": y, "z": z,"digOnly": True}
                result.result_str += f"尝试挖掘位置：{x},{y},{z}\n"
                call_result = await global_mcp_client.call_tool_directly("mine_block", args)
                is_success, result_content = parse_tool_result(call_result)
                if is_success:
                    result.result_str += translate_mine_block_tool_result(result_content)
                else:
                    result.result_str += f"挖掘失败: {result_content}"
        elif action_type == "place_block":
            block = action_json.get("block")
            position = action_json.get("position")
            x = math.floor(float(position.get("x")))
            y = math.floor(float(position.get("y")))
            z = math.floor(float(position.get("z")))
            
            result_str, args = await self.place_action.place_action(block, x, y, z)            
            result.result_str = result_str

            if not args:
                return result
            
            call_result = await global_mcp_client.call_tool_directly("place_block", args)
            is_success, result_content = parse_tool_result(call_result)
            result.result_str += translate_place_block_tool_result(result_content,args)
        elif action_type == "move":
            position = action_json.get("position")
            x = math.floor(float(position.get("x")))
            y = math.floor(float(position.get("y")))
            z = math.floor(float(position.get("z")))
            args = {"x": x, "y": y, "z": z, "type": "coordinate"}
            result.result_str = f"尝试移动到：{x},{y},{z}。\n"
            
            call_result = await global_mcp_client.call_tool_directly("move", args)
            is_success, result_content = parse_tool_result(call_result)
            result.result_str += translate_move_tool_result(result_content, args)
            return result
        elif action_type == "exit_mining_mode":
            mai_mode.mode = "main_mode"
            result.result_str = "退出采矿/采掘模式\n"
            return result
        
        return result
    
    async def excute_use_mode(self,action_json) -> ThinkingJsonResult:
        result = ThinkingJsonResult()
        action_type = action_json.get("action_type")
        
        if action_type == "collect_smelted_items":
            item = action_json.get("item")
            position = action_json.get("position")
            x = math.floor(float(position.get("x")))
            y = math.floor(float(position.get("y")))
            z = math.floor(float(position.get("z")))
            result.result_str = f"想要收集熔炼后的物品: {item}\n"
            if x and y and z:
                args = {"item": item, "x": x, "y": y, "z": z}
            else:
                args = {"item": item}
            call_result = await global_mcp_client.call_tool_directly("collect_smelted_items", args)
            is_success, result_content = parse_tool_result(call_result)
            if is_success:
                result.result_str += translate_collect_smelted_items_tool_result(result_content)
            else:
                result.result_str += f"收集熔炼物品失败: {result_content}"
        elif action_type == "start_smelting":
            item = action_json.get("item")
            fuel = action_json.get("fuel")
            count = action_json.get("count")
            result.result_str = f"想要开始熔炼: {item} 燃料: {fuel} 数量: {count}\n"
            args = {"item": item, "fuel": fuel, "count": count}
            call_result = await global_mcp_client.call_tool_directly("start_smelting", args)
            is_success, result_content = parse_tool_result(call_result)
            if is_success:
                result.result_str += translate_start_smelting_tool_result(result_content)
            else:
                result.result_str += f"开始熔炼失败: {result_content}"
        elif action_type == "place_block":
            block = action_json.get("block")
            position = action_json.get("position")
            x = math.floor(float(position.get("x")))
            y = math.floor(float(position.get("y")))
            z = math.floor(float(position.get("z")))
            result.result_str = f"想要放置方块: {block} 位置: {x},{y},{z}\n"
            args = {"block": block, "x": x, "y": y, "z": z}
            call_result = await global_mcp_client.call_tool_directly("place_block", args)
            is_success, result_content = parse_tool_result(call_result)
            result.result_str += translate_place_block_tool_result(result_content,args)
        elif action_type == "view_container":
            position = action_json.get("position", {})
            x = math.floor(float(position.get("x", 0)))
            y = math.floor(float(position.get("y", 0)))
            z = math.floor(float(position.get("z", 0)))
            type = action_json.get("type")
            args = {"x": x, "y": y, "z": z}
            result.result_str = f"想要查看{type}: {x},{y},{z}\n"
            result_content = await self.view_container.view_container(x, y, z, type)
            result.result_str += result_content
        elif action_type == "craft":
            item = action_json.get("item")
            count = action_json.get("count")
            result.result_str = f"想要合成: {item} 数量: {count}\n"
            self.inventory_old = global_environment.inventory
            
            ok, summary = await recipe_finder.craft_item_smart(item, count, global_environment.inventory, global_environment.block_position)
            if ok:
                result.result_str = f"合成成功：{item} x{count}\n{summary}\n"
            else:
                result.result_str = f"合成未完成：{item} x{count}\n{summary}\n"
        elif action_type == "use_chest":
            item = action_json.get("item")
            count = action_json.get("count", 1)
            type = action_json.get("type")
            position = action_json.get("position")
            x = math.floor(float(position.get("x")))
            y = math.floor(float(position.get("y")))
            z = math.floor(float(position.get("z")))
            result.result_str = f"想要使用箱子: {item} 类型: {type}\n"
            
            # 构建符合MCP工具期望的items格式
            items = [{"name": item, "count": count}]

            if type == "in":
                args = {"items": items, "action": "store", "x": x, "y": y, "z": z}
            elif type == "out":
                args = {"items": items, "action": "withdraw", "x": x, "y": y, "z": z}
            
            call_result = await global_mcp_client.call_tool_directly("use_chest", args)
            is_success, result_content = parse_tool_result(call_result) 
            translated_result = translate_use_chest_tool_result(result_content)
            result.result_str += translated_result
        elif action_type == "finish_using":
            reason = action_json.get("reason")
            result.result_str = f"结束使用方块模式: \n原因: {reason}\n"
            mai_mode.mode = "main_mode"
        else:
            self.logger.warning(f"在模式，{mai_mode.mode} 不支持的action_type: {action_type}")
            result.result_str = f"在模式，{mai_mode.mode} 不支持的action_type: {action_type}\n"
            mai_mode.mode = "main_mode"
            
        return result
            
    async def excute_memo(self,action_json) -> ThinkingJsonResult:
        result = ThinkingJsonResult()
        action_type = action_json.get("action_type")
        if action_type == "exit_memo_mode":
            mai_mode.mode = "main_mode"
        elif action_type == "add_memo":
            memo = action_json.get("memo")
            result.result_str = f"添加备忘录: {memo}\n"
            self.memo_list.append(memo)
        elif action_type == "remove_memo":
            memo = action_json.get("memo")
            result.result_str = f"移除备忘录: {memo}\n"
            self.memo_list.remove(memo)
        else:
            result.result_str = f"在模式，{mai_mode.mode} 不支持的action_type: {action_type}\n"
            self.logger.warning(f"在模式，{mai_mode.mode} 不支持的action_type: {action_type}")
            mai_mode.mode = "main_mode"
            
        return result

    async def excute_task_edit(self, action_json) -> ThinkingJsonResult:
        """
        执行json
        返回: ThinkingJsonResult
        """
        result = ThinkingJsonResult()
        action_type = action_json.get("action_type")
            
        if action_type == "change_task":
            new_task_id = action_json.get("new_task_id")
            reason  = action_json.get("reason")
            result.new_task_id = new_task_id
            result.result_str = f"选择更换到任务: {new_task_id},原因是: {reason}\n"
            self.on_going_task_id = new_task_id
            return result
        elif action_type == "delete_task":
            task_id = action_json.get("task_id")
            reason = action_json.get("reason")
            self.to_do_list.del_task_by_id(task_id)
            result.result_str = f"删除任务: {task_id},原因是: {reason}\n"
            return result
        elif action_type == "update_task_progress":
            progress = action_json.get("progress")
            done = action_json.get("done")
            task_id = action_json.get("task_id")
            result.task_id = task_id
            if done:
                result.done = done
                result.progress = progress
                result.result_str = f"任务({task_id})已完成"
                return result
            result.result_str = f"任务({task_id})进度已更新: {progress}"
            result.progress = progress
        elif action_type == "create_new_task":
            new_task = action_json.get("new_task")
            new_task_criteria = action_json.get("new_task_criteria")
            self.result_str = f"创建新任务: {new_task},原因: {new_task_criteria}\n"
            self.to_do_list.add_task(new_task, new_task_criteria)
        elif action_type == "exit_task_edit_mode":
            reason = action_json.get("reason")
            result.result_str = f"退出任务修改模式，原因是: {reason}\n"
            mai_mode.mode = "main_mode"
            return result
        
        return result
    
    async def _start_block_cache_viewer(self) -> None:
        """以后台线程启动方块缓存预览窗口。"""
        if self._viewer_started:
            return
        try:
            self.block_cache_viewer = BlockCacheViewer(update_interval_seconds=0.6)
            # 在单独线程中运行pygame，防止阻塞主线程
            self.block_cache_viewer.run_in_thread()
            # 启动overview更新异步任务
            if global_config.visual.enable:
                asyncio.create_task(self.block_cache_viewer.run_loop())
                self._viewer_started = True
                self.logger.info(" 方块缓存预览窗口已在单独线程中启动（每0.6秒刷新）")
                self.logger.info(" overview更新异步任务已启动（每10秒更新）")
        except Exception as e:
            self.logger.error(f" 启动方块缓存预览窗口失败: {e}")


    async def shutdown(self) -> None:
        """优雅关闭：停止环境更新器、关闭预览器、取消后台任务。"""
        try:
            if self.environment_updater:
                self.environment_updater.stop()
        except Exception:
            pass
        try:
            if self.block_cache_viewer:
                self.block_cache_viewer.stop()
        except Exception:
            pass
        # 取消后台任务
        for task in (self.exec_task):
            try:
                if task and not task.done():
                    task.cancel()
            except Exception:
                pass

