import asyncio
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
    convert_mcp_tools_to_openai_format, parse_tool_result, filter_action_tools,
    parse_thinking, parse_json,extract_code_from_markdown
)   
from agent.to_do_list import ToDoList
from agent.smart_craft.craft_action import recipe_finder
import traceback
from agent.block_cache.nearby_block import NearbyBlockManager
from view_render.block_cache_viewer import BlockCacheViewer
from agent.fixed_actions.place_action import place_action
from agent.fixed_actions.move_action import move_action
from agent.fixed_actions.use_chest_action import use_chest as fixed_use_chest
from agent.fixed_actions.use_furnace_action import use_furnace as fixed_use_furnace
from agent.utils.utils_tool_translation import (
    translate_move_tool_result, 
    translate_mine_block_tool_result, 
    translate_place_block_tool_result, 
    translate_chat_tool_result,
    translate_use_chest_tool_result,
    translate_eat_tool_result
)
from agent.fixed_actions.view_container_action import view_container as fixed_view_container
from mcp_server.client import global_mcp_client
from agent.code_runner import code_runner
from agent.thinking_log import global_thinking_log
from agent.mai_mode import mai_mode
from agent.environment.basement import global_basement
from agent.environment.locations import global_location_points
from agent.environment.basic_info import BlockPosition
import os
import datetime
import ast
import re
import json
from agent.action_learner import action_learner
from agent.actions_manager import ActionsManager

COLOR_MAP = {
    "main_mode": "\033[32m",        # 绿色
    "move_mode": "\033[38;5;141m",  # 橙色
    "mining_mode": "\033[38;5;226m",  # 黄色
    "chat_mode": "\033[38;5;51m",     # 青色
    "memo_mode": "\033[38;5;199m",    # 粉色
    "task_edit_mode": "\033[38;5;196m", # 红色
    "use_block": "\033[38;5;208m", # 橙色
}



class ThinkingJsonResult:
    def __init__(self):
        self.result_str = ""
        self.done = False
        self.new_task = ""
        self.new_task_id = ""
        self.progress = ""
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
        
        # 初始化LLM和工具适配器
        # 延迟初始化
        self.tools: Optional[List[BaseTool]] = None

        # 环境更新器
        self.environment_updater: Optional[EnvironmentUpdater] = None
        self.nearby_block_manager: Optional[NearbyBlockManager] = None

        # 视图容器查看改为固定动作函数
        # 初始化状态
        self.initialized = False
        
        self.goal = global_config.game.goal
        
        self.on_going_task_id = ""
        
        self.to_do_list: ToDoList = ToDoList()
        
        # 动作管理器
        self.actions_manager: ActionsManager = ActionsManager()
        
        # 方块缓存预览窗口
        self.block_cache_viewer: Optional[BlockCacheViewer] = None
        self._viewer_started: bool = False
        self.exec_task: Optional[asyncio.Task] = None


        self.input_data = {}
        
        
    async def initialize(self):
        """异步初始化"""
        try:
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


            self.tools = await global_mcp_client.get_tools_metadata()
            self.action_tools = filter_action_tools(self.tools)
            self.logger.info(f" 获取到 {len(self.action_tools)} 个可用工具")
            self.openai_tools = convert_mcp_tools_to_openai_format(self.action_tools)

            await self._start_block_cache_viewer()
            
            # 创建并启动环境更新器
            self.environment_updater = EnvironmentUpdater(
                update_interval=0.1,  # 默认5秒更新间隔
            )
            
            # 固定动作无需实例化
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


            await self.environment_updater.perform_update()
            environment_info = global_environment.get_summary()
            nearby_block_info = await self.nearby_block_manager.get_block_details_mix_str(global_environment.block_position,distance=8)
            self.input_data = {
                "task": "",
                "environment": environment_info,
                "thinking_list": global_thinking_log.get_thinking_log(),
                "nearby_block_info": nearby_block_info,
                "position": global_environment.get_position_str(),
                "location_list": global_location_points.all_location_str(),
                "chat_str": global_environment.get_chat_str(),
                "event_str": global_environment.get_event_str(),
                "to_do_list": self.to_do_list.__str__(),
                "task_list": self.to_do_list.__str__(),
                "goal": self.goal,
                "mode": mai_mode.mode,
                "inventory_str": global_environment.get_inventory_str(),
                "self_str": global_environment.get_self_str(),
                "retrieved_skills": self.actions_manager.get_all_learnt_actions_string(),
            }
            

        except Exception as e:
            self.logger.error(f" 初始化失败: {e}")
            raise
        
    async def update_input_data(self):
        await self.environment_updater.perform_update()
        environment_info = global_environment.get_summary()
        nearby_block_info = await self.nearby_block_manager.get_block_details_mix_str(global_environment.block_position,distance=8)
        self.input_data["environment"] = environment_info
        self.input_data["thinking_list"] = global_thinking_log.get_thinking_log()
        self.input_data["nearby_block_info"] = nearby_block_info
        self.input_data["position"] = global_environment.get_position_str()
        self.input_data["location_list"] = global_location_points.all_location_str()
        self.input_data["chat_str"] = global_environment.get_chat_str()
        self.input_data["event_str"] = global_environment.get_event_str()
        self.input_data["to_do_list"] = self.to_do_list.__str__()
        self.input_data["task_list"] = self.to_do_list.__str__()
        self.input_data["goal"] = self.goal
        self.input_data["mode"] = mai_mode.mode
        self.input_data["inventory_str"] = global_environment.get_inventory_str()
        self.input_data["self_str"] = global_environment.get_self_str()
        self.input_data["retrieved_skills"] = self.actions_manager.get_all_learnt_actions_string()
      
    async def run_execute_loop(self):
        """
        运行执行循环
        """
        self.on_going_task_id = ""
        mai_mode.mode = "main_mode"
        while True:
            await self.next_thinking()


    async def next_thinking(self) -> TaskResult:
        """
        执行目标
        返回: (执行结果, 执行状态)
        """
        try:

            # await self.update_input_data()
            
            # if mai_mode.need_chat:
            #     prompt = prompt_manager.generate_prompt("chat_mode", **self.input_data)
            #     thinking = await self.llm_client.simple_chat(prompt)
            #     # self.logger.info(f" 原始输出: {thinking}")            
            #     self.logger.info(f"\033[38;5;208m chat提示词: {prompt}\033[0m")
            #     result = await self.excute_chat(thinking)
            #     global_thinking_log.add_thinking_log(f"你使用chat进行了发言：{result.result_str}",type = "notice")
            #     self.logger.info(f" 你的发言: {result.result_str}")
            #     mai_mode.need_chat = False
            #     return TaskResult()
            
            
            await self.update_input_data()
            plan_prompt = prompt_manager.generate_prompt("plan_task", **self.input_data)
            plan_thinking = await self.llm_client.simple_chat(plan_prompt)
            
            self.logger.info(f" 规划提示词: {plan_prompt}")
            self.logger.info(f" 规划结果: {plan_thinking}")
            
            success_plan, plan_thinking, plan_json, plan_before = parse_thinking(plan_thinking)
            
            # self.logger.info(f" 规划结果: {plan_json}")
            task = self.to_do_list.add_task(plan_json.get("target"), plan_json.get("reson"), plan_json.get("evaluation"))
            
            
            
            self.input_data["task"] = task.__str__()       
            self.input_data["adjust_reason"] = ""
            self.input_data["retrieved_skills"] = self.actions_manager.get_all_learnt_actions_string()
            self.input_data["code_last_run"] = ""
            self.input_data["output_last_run"] = ""
            self.input_data["error_last_run"] = ""
            
            await self.update_input_data()
            game_info_before = prompt_manager.generate_prompt("game_info", **self.input_data)
            self.input_data["game_info_before"] = game_info_before
            
            
            task_finished = False
            max_try = 5
            try_count = 0
            while not task_finished:
                code, success, output, error, traceback = await self.excute_code_generate(self.input_data)
                if success:
                    self.input_data["code_last_run"] = code
                    self.input_data["output_last_run"] = output
                    self.input_data["error_last_run"] = "代码执行成功"
                else:
                    self.input_data["code_last_run"] = code
                    self.input_data["output_last_run"] = output
                    self.input_data["error_last_run"] = error + "\n" + traceback
                    continue
                    # 重新生成

                await self.update_input_data()
                game_info_after = prompt_manager.generate_prompt("game_info", **self.input_data)
                self.input_data["game_info_after"] = game_info_after                
                
                await self.update_input_data()
                reviewer_prompt = prompt_manager.generate_prompt("reviewer", **self.input_data)
                reviewer_thinking = await self.llm_client.simple_chat(reviewer_prompt)
                # self.logger.info(f" 审查提示词: {reviewer_prompt}")
                self.logger.info(f" 审查结果: {reviewer_thinking}")
                revier_json = parse_json(reviewer_thinking)
                success_task = revier_json.get("success")
                if success_task:
                    # 任务成功，保存学到的动作代码
                    try:
                        await action_learner.save_learnt_action_code(code)
                    except Exception:
                        self.logger.error(f" 保存学到的动作代码失败: {traceback.format_exc()}")
                    task_finished = True
                    task.done = True
                else:
                    self.input_data["adjust_reason"] = revier_json.get("reason")
                    
                try_count +=1
                if try_count > max_try:
                    self.logger.error(f" 任务执行失败，重试次数超过{max_try}次")
                    task.done = False
                    break
            

            # basic_info_prompt = prompt_manager.generate_prompt("basic_info", **input_data)
            # mode_prompt = prompt_manager.generate_prompt("main_thinking", **input_data)
            # prompt = basic_info_prompt + mode_prompt
            # self.logger.info(f" 执行任务提示词: {prompt}")

            
            # thinking = await self.llm_client.simple_chat(prompt)
            # # self.logger.info(f" 原始输出: {thinking}")                
            
            # success, thinking, json_obj, thinking_log = parse_thinking(thinking)
            
            # #出现意外的调试
            # if not success or not json_obj:
            #     self.logger.warning(f" 思考结果中没有json对象: {thinking}")
            #     return TaskResult()
            
            # action_type = json_obj.get("action_type")
            # if not action_type:
            #     self.logger.warning(f" 思考结果中没有action_type: {thinking}")
            #     return TaskResult()
            
            
            # color_prefix = COLOR_MAP.get(mai_mode.mode, "\033[0m")
            
            # if thinking_log:
            #     global_thinking_log.add_thinking_log(thinking_log,type = "thinking")
                
            # self.logger.info(f"{color_prefix} 想法{mai_mode.mode}: {thinking_log}\033[0m")
            
            # if json_obj:
            #     self.logger.info(f"{color_prefix} 动作: {json_obj}\033[0m")
            #     global_thinking_log.add_thinking_log(f"执行动作：{json_obj}",type = "action")
            #     result = await self.excute_main_mode(json_obj)
            #     global_thinking_log.add_thinking_log(f"执行结果：{result.result_str}",type = "notice")
                
            #     self.logger.info(f" 执行结果: {result.result_str}")
                
                
        except Exception:
            await asyncio.sleep(1)
            self.logger.error(f" 任务执行异常: {traceback.format_exc()}")
            
        
    async def excute_code_generate(self,input_data:dict):
        await self.update_input_data()
        prompt = prompt_manager.generate_prompt("code_generate", **input_data)
        code_and_plan = await self.llm_client.simple_chat(prompt)
        self.logger.info(f" 代码生成提示词: {prompt}")
        self.logger.info(f" 代码生成结果: {code_and_plan}")
        # 解析代码块
        extracted_code = extract_code_from_markdown(code_and_plan)
        
        # 运行解析出的代码（支持异步函数）
        execution_result = None
        if extracted_code:
            # self.logger.info(f"开始运行生成的代码:\n{extracted_code}")
            execution_result = await code_runner.run_code_async(extracted_code)
            
            if execution_result["success"]:
                self.logger.info("代码执行成功")
                if execution_result["output"]:
                    self.logger.info(f"代码输出: {execution_result['output']}")
            else:
                self.logger.error(f"代码执行失败: {execution_result['error']}")
                if execution_result["traceback"]:
                    self.logger.error(f"错误堆栈: {execution_result['traceback']}")


        return extracted_code,execution_result["success"],execution_result['output'],execution_result['error'],execution_result["traceback"]



        
    async def excute_chat(self,thinking_str) -> ThinkingJsonResult:
        message = thinking_str.strip().replace('\n', '').replace('\r', '')
        args = {"message": message}
        call_result = await global_mcp_client.call_tool_directly("chat", args)
        is_success, result_content = parse_tool_result(call_result)
        result = ThinkingJsonResult()
        result.result_str += translate_chat_tool_result(result_content)
        mai_mode.mode = "main_mode"
        return result
        
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
            move_and_collet = action_json.get("move_and_collet")
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
            args = {"x": x, "y": y, "z": z,"digOnly": not move_and_collet}
            result.result_str = f"尝试破坏位置：{x},{y},{z}，并前往搜集\n"
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
            
            result_str = await place_action(block, x, y, z)
            result.result_str = result_str
            return result
        elif action_type == "chat":
            message = action_json.get("message")
            if message is not None:
                message = message.strip().replace('\n', '').replace('\r', '')
            args = {"message": message}
            call_result = await global_mcp_client.call_tool_directly("chat", args)
            is_success, result_content = parse_tool_result(call_result)
            result.result_str += translate_chat_tool_result(result_content)
            return result
        elif action_type == "eat":
            item = action_json.get("item")
            result.result_str = f"想要食用: {item}\n"
            args = {"itemName": item, "useType":"consume"} #consume表示食用
            call_result = await global_mcp_client.call_tool_directly("use_item", args)
            is_success, result_content = parse_tool_result(call_result)
            self.logger.info(f"食用结果: {result_content}")
            result.result_str += translate_eat_tool_result(result_content)
        elif action_type == "enter_use_block_mode":
            reason = action_json.get("reason")
            result.result_str = f"进入use_block模式，原因是: {reason}\n"
            mai_mode.mode = "use_block"
            return result
        else:
            self.logger.warning(f" {mai_mode.mode} 不支持的action_type: {action_type}")
            
            
        return result

            
    async def excute_use_item(self,action_json) -> ThinkingJsonResult:
        result = ThinkingJsonResult()
        action_type = action_json.get("action_type")
        if action_type == "eat":
            item = action_json.get("item")
            result.result_str = f"想要食用: {item}\n"
            args = {"itemName": item, "useType":"consume"} #consume表示食用
            call_result = await global_mcp_client.call_tool_directly("use_item", args)
            is_success, result_content = parse_tool_result(call_result)
            self.logger.info(f"食用结果: {result_content}")
            # result.result_str += translate_eat_tool_result(result_content)
        elif action_type == "use_item":
            item = action_json.get("item")
            result.result_str = f"想要使用: {item}\n"
            args = {"itemName": item,"useType":"activate"} #activate表示激活
            call_result = await global_mcp_client.call_tool_directly("use_item", args)
            is_success, result_content = parse_tool_result(call_result)
            self.logger.info(f"使用结果: {result_content}")
            # result.result_str += translate_use_item_tool_result(result_content)
        elif action_type == "use_item_on_entity":
            item = action_json.get("item")
            entity = action_json.get("entity")
            result.result_str = f"想要使用: {item} 在: {entity}\n"
            args = {"itemName": item, "targetEntityName": entity,"useType":"useOn"} #useOnEntity表示使用在实体上
            call_result = await global_mcp_client.call_tool_directly("use_item", args)
            is_success, result_content = parse_tool_result(call_result)
            self.logger.info(f"使用结果: {result_content}")
            # result.result_str += translate_use_item_on_entity_tool_result(result_content)
        elif action_type == "exit_use_item_mode":
            reason = action_json.get("reason")
            result.result_str = f"退出使用物品模式: \n原因: {reason}\n"
            mai_mode.mode = "main_mode"
        else:
            self.logger.warning(f"在模式，{mai_mode.mode} 不支持的action_type: {action_type}")
            result.result_str = f"在模式，{mai_mode.mode} 不支持的action_type: {action_type}\n"
            mai_mode.mode = "main_mode"
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

