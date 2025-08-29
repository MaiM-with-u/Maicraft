import asyncio
import time
import math
from typing import List, Any, Optional
from langchain_core.tools import BaseTool
from utils.logger import get_logger
from config import global_config
from openai_client.llm_request import LLMClient
from openai_client.modelconfig import ModelConfig
from agent.environment_updater import EnvironmentUpdater
from agent.environment import global_environment
from agent.prompt_manager.prompt_manager import prompt_manager
from agent.block_cache.block_cache import global_block_cache
from agent.prompt_manager.template import init_templates
from agent.utils import (
    parse_json, convert_mcp_tools_to_openai_format, parse_tool_result, filter_action_tools,
    parse_thinking,
)
from agent.to_do_list import ToDoList
from agent.action.craft_action.craft_action import recipe_finder
import traceback
from agent.nearby_block import NearbyBlockManager
from view_render.block_cache_viewer import BlockCacheViewer
from agent.action.place_action import PlaceAction
from agent.action.move_action import MoveAction
from .utils_tool_translation import (
    translate_move_tool_result, 
    translate_mine_nearby_tool_result, 
    translate_mine_block_tool_result, 
    translate_place_block_tool_result, 
    translate_chat_tool_result,
    translate_start_smelting_tool_result,
    translate_collect_smelted_items_tool_result,
    translate_view_chest_result,
)
from agent.action.view_container import ViewContainer

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
    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
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

        self.goal = "以合适的步骤挖到3个钻石，制作成钻石镐"

        self.memo_list: list[str] = []
        
        self.on_going_task_id = ""
        
        self.thinking_list: list[str] = []
        
        
        self.to_do_list: ToDoList = ToDoList()
        self.task_done_list: list[tuple[bool, str, str]] = []
        
        # 方块缓存预览窗口
        self.block_cache_viewer: Optional[BlockCacheViewer] = None
        self._viewer_started: bool = False
        self._plan_task: Optional[asyncio.Task] = None
        self._exec_task: Optional[asyncio.Task] = None
        self._viewer_task: Optional[asyncio.Task] = None
        
        
    async def initialize(self):
        """异步初始化"""
        try:
            self.logger.info("[MaiAgent] 开始初始化")
            
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
            
            
            self.logger.info("[MaiAgent] LLM客户端初始化成功")
            
            
            self.tools = await self.mcp_client.get_tools_metadata()
            self.action_tools = filter_action_tools(self.tools)
            self.logger.info(f"[MaiAgent] 获取到 {len(self.action_tools)} 个可用工具")
            self.openai_tools = convert_mcp_tools_to_openai_format(self.action_tools)

            # await self._start_block_cache_viewer()
            
            # 创建并启动环境更新器
            self.environment_updater = EnvironmentUpdater(
                mcp_client = self.mcp_client,
                update_interval=0.1,  # 默认5秒更新间隔
            )
            
            self.place_action = PlaceAction()
            self.move_action = MoveAction()
            self.view_container = ViewContainer(self.mcp_client)
            # 启动环境更新器
            if self.environment_updater.start():
                self.logger.info("[MaiAgent] 环境更新器启动成功")
            else:
                self.logger.error("[MaiAgent] 环境更新器启动失败")

            await asyncio.sleep(1)
            
            self.mode = "main_action"
            
            # 初始化NearbyBlockManager
            self.nearby_block_manager = NearbyBlockManager(global_config)
            self.logger.info("[MaiAgent] NearbyBlockManager初始化成功")

            self.initialized = True
            self.logger.info("[MaiAgent] 初始化完成")

            # 启动方块缓存预览窗口（后台，不阻塞事件循环）
            
            self.inventory_old:List[Any] = []
            
            

        except Exception as e:
            self.logger.error(f"[MaiAgent] 初始化失败: {e}")
            raise
        
        
    async def run_plan_loop(self):
        """
        运行主循环
        """
        while True:            
            try:
                await self.propose_all_task(to_do_list=self.to_do_list, environment_info=global_environment.get_summary())
            except Exception:
                import traceback
                self.logger.error(f"[MaiAgent] propose_all_task 调用异常: {traceback.format_exc()}")
            while True:
                if self.to_do_list.check_if_all_done():
                    self.logger.info(f"[MaiAgent] 所有任务已完成，目标{self.goal}完成")
                    self.to_do_list.clear()
                    self.goal_list.append((self.goal, "done", "所有任务已完成"))
                    await asyncio.sleep(1)
                    break
                await asyncio.sleep(5)
                
    async def run_execute_loop(self):
        """
        运行执行循环
        """
        self.on_going_task_id = ""
        while True:
            if len(self.to_do_list.items) == 0:
                self.logger.info("[MaiAgent] 任务列表为空，等待任务列表更新")
                await asyncio.sleep(1)
                continue

            result = await self.execute_next_task()
            
            if result.status == "done":
                self.logger.info(f"[MaiAgent] 任务执行成功: {result.message}")
                self.task_done_list.append((True,self.on_going_task_id,"任务完成"))
                self.on_going_task_id = ""
            elif result.status == "new_task":
                self.logger.info(f"[MaiAgent] 创建新任务: {result.message}")
                self.task_done_list.append((True,self.on_going_task_id,"任务未完成，需要完成前置任务"))
            elif result.status == "change":
                self.logger.info(f"[MaiAgent] 更换任务: {result.message}")
                self.task_done_list.append((True,self.on_going_task_id,f"任务未完成，更换到任务{result.new_task_id}"))

    
    async def propose_all_task(self, to_do_list: ToDoList, environment_info: str) -> bool:
        self.logger.info("[MaiAgent] 开始提议任务")
        # 使用原有的提示词模板，但通过call_tool传入工具
        await self.environment_updater.perform_update()
        nearby_block_info = await self.nearby_block_manager.get_block_details_mix_str(global_environment.block_position)
        input_data = {
            "goal": self.goal,
            "environment": environment_info,
            "to_do_list": to_do_list.__str__(),
            "nearby_block_info": nearby_block_info,
            "position": global_environment.get_position_str(),
            "chat_str": global_environment.get_chat_str(),
        }
        prompt = prompt_manager.generate_prompt("minecraft_to_do", **input_data)
        self.logger.info(f"[MaiAgent] 任务提议提示词: {prompt}")
        
        response = await self.llm_client.simple_chat(prompt)
        self.logger.info(f"[MaiAgent] 任务提议响应: {response}")
        
        tasks_list = parse_json(response)
        if tasks_list.get("tasks",""):
            tasks_list = tasks_list.get("tasks",[])
        
        for task in tasks_list:
            try:
                details = str(task.get("details", "")).strip()
                done_criteria = str(task.get("done_criteria", "")).strip()
                self.to_do_list.add_task(details=details, done_criteria=done_criteria)
            except Exception as e:
                self.logger.error(f"[MaiAgent] 处理任务时异常: {e}，任务内容: {task}")
                continue
        
        return True

    async def _start_block_cache_viewer(self) -> None:
        """以后台线程启动方块缓存预览窗口。"""
        if self._viewer_started:
            return
        try:
            self.block_cache_viewer = BlockCacheViewer(update_interval_seconds=0.6)
            # 使用主事件循环任务运行pygame，保证Ctrl+C能够打断
            import asyncio
            asyncio.create_task(self.block_cache_viewer.run_loop())
            self._viewer_task = asyncio.create_task(self.block_cache_viewer.run_async())
            self._viewer_started = True
            self.logger.info("[MaiAgent] 方块缓存预览窗口已启动（每3秒刷新）")
        except Exception as e:
            self.logger.error(f"[MaiAgent] 启动方块缓存预览窗口失败: {e}")

    
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


    async def execute_next_task(self) -> TaskResult:
        """
        执行目标
        返回: (执行结果, 执行状态)
        """
        try:
            task_result = TaskResult()
            
            
            if not self.on_going_task_id:
                self.mode = "task_action"
                task = None
            else:
                task = self.to_do_list.get_task_by_id(self.on_going_task_id)
                if task is None:
                    task_result.status = "rechoice"
                    task_result.message = f"任务不存在: {self.on_going_task_id}"
                    return task_result
                else:
                    if self.mode == "task_action":
                        self.mode = "main_action"
            
            
            
            # 限制思考上下文
            while True:
                if len(self.thinking_list) > 20:
                    self.thinking_list = self.thinking_list[-20:]
                    
                if task:
                    self.logger.info(f"[MaiAgent]执行任务:\n {task}")
                else:
                    self.logger.info("[MaiAgent] 没有任务，开始选择任务")
                
                # 获取当前环境信息
                await self.environment_updater.perform_update()
                environment_info = global_environment.get_summary()
                nearby_block_info = await self.nearby_block_manager.get_block_details_mix_str(global_environment.block_position)
                # executed_tools_str = self._format_executed_tools_history(executed_tools_history[-10:]) if executed_tools_history else ""
                
                # 使用原有的提示词模板，但通过call_tool传入工具
                input_data = {
                    "task": task.__str__(),
                    "environment": environment_info,
                    # "executed_tools": executed_tools_str,
                    "thinking_list": "\n".join(self.thinking_list),
                    "nearby_block_info": nearby_block_info,
                    "position": global_environment.get_position_str(),
                    "memo_list": "\n".join(self.memo_list),
                    "chat_str": global_environment.get_chat_str(),
                }
                
                
                if self.mode == "main_action":
                    input_data["goal"] = self.goal
                    prompt = prompt_manager.generate_prompt("minecraft_excute_task_thinking", **input_data)
                    # self.logger.info(f"[MaiAgent] 执行任务提示词: {prompt}")
                elif self.mode == "task_action":
                    input_data["to_do_list"] = self.to_do_list.__str__()
                    input_data["task_done_list"] = self._format_task_done_list()
                    input_data["goal"] = self.goal
                    prompt = prompt_manager.generate_prompt("minecraft_excute_task_action", **input_data)
                    # self.logger.info(f"\033[38;5;153m[MaiAgent] 执行任务提示词: {prompt}\033[0m")
                elif self.mode == "move_action":
                    prompt = prompt_manager.generate_prompt("minecraft_excute_move_action", **input_data)
                    # self.logger.info(f"\033[38;5;208m[MaiAgent] 执行任务提示词: {prompt}\033[0m")
                elif self.mode == "container_action":
                    prompt = prompt_manager.generate_prompt("minecraft_excute_container_action", **input_data)
                    # self.logger.info(f"\033[38;5;208m[MaiAgent] 执行任务提示词: {prompt}\033[0m")
                elif self.mode == "mining_mode":
                    input_data["goal"] = self.goal
                    nearby_block_info = await self.nearby_block_manager.get_block_details_mix_str(global_environment.block_position,6)
                    prompt = prompt_manager.generate_prompt("minecraft_mining_nearby", **input_data)
                    # self.logger.info(f"\033[38;5;208m[MaiAgent] 执行任务提示词: {prompt}\033[0m")
                
                
                
                thinking = await self.llm_client.simple_chat(prompt)
                # self.logger.info(f"[MaiAgent] 任务想法: {thinking}")
                
                json_obj, json_before = parse_thinking(thinking)
                
                time_str = time.strftime("%H:%M:%S", time.localtime())
                
                if json_obj:
                    color_map = {
                        "main_action": "\033[32m",        # 绿色
                        "task_action": "\033[38;5;39m",   # 蓝色
                        "move_action": "\033[38;5;208m",  # 橙色
                        "container_action": "\033[38;5;141m", # 紫色
                        "mining_mode": "\033[38;5;226m",  # 黄色
                    }
                    color_prefix = color_map.get(self.mode, "\033[0m")
                    self.logger.info(f"{color_prefix}[MaiAgent] 想法{self.mode}: {json_before}\033[0m")
                    self.logger.info(f"{color_prefix}[MaiAgent] 动作: {json_obj}\033[0m")
                    
                    if json_before:
                        self.thinking_list.append(f"时间：{time_str} 思考结果：{json_before}")
                    
                    result = await self.excute_json(json_obj)
                    
                    self.logger.info(f"[MaiAgent] 执行结果: {result.result_str}")
                    
                    self.thinking_list.append(f"时间：{time_str} 执行结果：{result.result_str}")
                    if result.done:
                        update_task = self.to_do_list.get_task_by_id(result.task_id)
                        if update_task:
                            update_task.done = result.done
                            update_task.progress = result.progress
                            task_result.status = "done"
                            task_result.message = f"任务执行成功: {update_task.__str__()}"
                            return task_result
                    elif result.new_task:
                        task_result.status = "new_task"
                        task_result.message = f"新任务: {result.new_task}"
                        return task_result
                    elif result.progress:
                        update_task = self.to_do_list.get_task_by_id(result.task_id)
                        if update_task:
                            update_task.progress = result.progress
                    elif result.new_task_id:
                        task_result.status = "change"
                        task_result.message = f"当前任务未完成，切换到任务: {result.new_task_id}"
                        task_result.new_task_id = result.new_task_id
                        return task_result
                    elif result.rewrite:
                        task_result.status = "rewrite"
                        task_result.message = f"修改任务列表: {result.rewrite}"
                        task_result.rewrite = result.rewrite
                        return task_result
                        
                        
                else:
                    self.logger.info(f"[MaiAgent] 想法: {json_before}")
                    if json_before:
                        self.thinking_list.append(f"时间：{time_str} 思考结果：{json_before}")
                    

        except Exception as e:
            self.logger.error(f"[MaiAgent] 任务执行异常: {traceback.format_exc()}")
            task_result.status = "rechoice"
            task_result.message = f"任务执行异常: {str(e)}"
            return task_result

    async def excute_json(self, json_obj: dict) -> ThinkingJsonResult:
        """
        执行json
        返回: ThinkingJsonResult
        """
        result = ThinkingJsonResult()
        action_type = json_obj.get("action_type")
        
        if self.mode == "move_action":
            x=json_obj.get("x")
            y=json_obj.get("y")
            z=json_obj.get("z")
            args = {"x": x, "y": y, "z": z, "type": "coordinate"}
            result.result_str = f"尝试移动到：{x},{y},{z}\n"
            
            call_result = await self.mcp_client.call_tool_directly("move", args)
            is_success, result_content = parse_tool_result(call_result)
            result.result_str += translate_move_tool_result(result_content, args)

            self.mode = "main_action"
            return result
        elif self.mode == "mining_mode":
            if action_type == "mine_nearby":
                name = json_obj.get("name")
                count = json_obj.get("count")
                result.result_str = f"想要批量挖掘: {name} 数量: {count}\n"
                args = {"name": name, "count": count}
                call_result = await self.mcp_client.call_tool_directly("mine_block", args)
                is_success, result_content = parse_tool_result(call_result)
                if is_success:
                    result.result_str += translate_mine_nearby_tool_result(result_content)
                else:
                    result.result_str += f"批量挖掘失败: {result_content}"
            elif action_type == "mine_block":
                x = math.floor(float(json_obj.get("x")))
                y = math.floor(float(json_obj.get("y")))
                z = math.floor(float(json_obj.get("z")))
                block_cache = global_block_cache.get_block(x, y, z)
                if block_cache.block_type == "air":
                    result.result_str += f"位置{x},{y},{z}不存在方块，无法挖掘\n"
                    return result
                if block_cache.block_type == "water" or block_cache.block_type == "lava" or block_cache.block_type == "bedrock":
                    result.result_str += f"位置{x},{y},{z}是{block_cache.block_type}，无法挖掘\n"
                    return result
                
                args = {"x": x, "y": y, "z": z,"digOnly": True}
                result.result_str = f"尝试挖掘位置：{x},{y},{z}\n"
                call_result = await self.mcp_client.call_tool_directly("mine_block", args)
                is_success, result_content = parse_tool_result(call_result)
                if is_success:
                    result.result_str += translate_mine_block_tool_result(result_content)
                else:
                    result.result_str += f"挖掘失败: {result_content}"
            elif action_type == "place_block":
                block = json_obj.get("block")
                x = json_obj.get("x")
                y = json_obj.get("y")
                z = json_obj.get("z")
                
                result_str, args = await self.place_action.place_action(block, x, y, z)            
                result.result_str = result_str

                if not args:
                    return result
                
                call_result = await self.mcp_client.call_tool_directly("place_block", args)
                is_success, result_content = parse_tool_result(call_result)
                result.result_str += translate_place_block_tool_result(result_content,args)
            elif action_type == "move":
                self.mode = "move_action"
                reason = json_obj.get("reason")
                result.result_str = f"选择进行移动动作: \n原因: {reason}\n"            
                return result
            elif action_type == "exit_mining_mode":
                self.mode = "main_action"
                result.result_str = "退出采矿/采掘模式\n"
                return result
        elif self.mode == "container_action":
            if action_type == "collect_smelted_items":
                item = json_obj.get("item")
                x = json_obj.get("x")
                y = json_obj.get("y")
                z = json_obj.get("z")
                result.result_str = f"想要收集熔炼后的物品: {item}\n"
                if x and y and z:
                    args = {"item": item, "x": x, "y": y, "z": z}
                else:
                    args = {"item": item}
                call_result = await self.mcp_client.call_tool_directly("collect_smelted_items", args)
                is_success, result_content = parse_tool_result(call_result)
                if is_success:
                    result.result_str += translate_collect_smelted_items_tool_result(result_content)
                else:
                    result.result_str += f"收集熔炼物品失败: {result_content}"
            elif action_type == "start_smelting":
                item = json_obj.get("item")
                fuel = json_obj.get("fuel")
                count = json_obj.get("count")
                result.result_str = f"想要开始熔炼: {item} 燃料: {fuel} 数量: {count}\n"
                args = {"item": item, "fuel": fuel, "count": count}
                call_result = await self.mcp_client.call_tool_directly("start_smelting", args)
                is_success, result_content = parse_tool_result(call_result)
                if is_success:
                    result.result_str += translate_start_smelting_tool_result(result_content)
                else:
                    result.result_str += f"开始熔炼失败: {result_content}"
            elif action_type == "view_chest":
                x = math.floor(float(json_obj.get("x")))
                y = math.floor(float(json_obj.get("y")))
                z = math.floor(float(json_obj.get("z")))
                args = {"x": x, "y": y, "z": z}
                result.result_str = f"想要查看: {x},{y},{z}\n"
                result_content = await self.view_container.view_chest(x, y, z)
                result.result_str += translate_view_chest_result(result_content)
            elif action_type == "craft":
                item = json_obj.get("item")
                count = json_obj.get("count")
                result.result_str = f"想要合成: {item} 数量: {count}\n"
                self.inventory_old = global_environment.inventory
                
                ok, summary = await recipe_finder.craft_item_smart(item, count, global_environment.inventory, global_environment.block_position)
                if ok:
                    result.result_str = f"合成成功：{item} x{count}\n{summary}\n"
                else:
                    result.result_str = f"合成未完成：{item} x{count}\n{summary}\n"
            elif action_type == "use_chest":
                item = json_obj.get("item")
                type = json_obj.get("type")
                result.result_str = f"想要使用箱子: {item} 类型: {type}\n"
                if type == "in":
                    args = {"item": item, "action": "store"}
                elif type == "out":
                    args = {"item": item, "action": "withdraw"}
                call_result = await self.mcp_client.call_tool_directly("use_chest", args)
                is_success, result_content = parse_tool_result(call_result)
                result.result_str += result_content
            elif action_type == "finish_using":
                self.mode = "main_action"
            else:
                self.logger.warning(f"在合成模式，{self.mode} 不支持的action_type: {action_type}")
                self.mode = "main_action"
        elif self.mode == "task_action":
            if action_type == "change_task":
                new_task_id = json_obj.get("new_task_id")
                reason  = json_obj.get("reason")
                result.new_task_id = new_task_id
                result.result_str = f"选择更换任务: {new_task_id},原因是: {reason}\n"
                self.on_going_task_id = new_task_id
                return result
            elif action_type == "delete_task":
                task_id = json_obj.get("task_id")
                reason = json_obj.get("reason")
                self.to_do_list.del_task_by_id(task_id)
                result.result_str = f"删除任务: {task_id},原因是: {reason}\n"
                self.mode = "task_action"
                return result
            elif action_type == "update_task_progress":
                progress = json_obj.get("progress")
                done = json_obj.get("done")
                task_id = json_obj.get("task_id")
                
                result.task_id = task_id
                
                if done:
                    result.done = done
                    result.progress = progress
                    result.result_str = f"任务({task_id})已标记为完成"
                    self.mode = "main_action"
                    return result
                result.result_str = f"任务({task_id})进度已更新: {progress}"
                result.progress = progress
                self.mode = "main_action"
            elif action_type == "create_new_task":
                new_task = json_obj.get("new_task")
                new_task_criteria = json_obj.get("new_task_criteria")
                
                # 创建并执行新任务
                new_task_item = self.to_do_list.add_task(new_task, new_task_criteria)
                self.on_going_task_id = new_task_item.id
                self.mode = "main_action"
        else:
            if action_type == "move":
                self.mode = "move_action"
                reason = json_obj.get("reason")
                result.result_str = f"选择进行移动动作: \n原因: {reason}\n"            
                return result
            elif action_type == "break_block":
                x = math.floor(float(json_obj.get("x")))
                y = math.floor(float(json_obj.get("y")))
                z = math.floor(float(json_obj.get("z")))
                
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
                call_result = await self.mcp_client.call_tool_directly("mine_block", args)
                is_success, result_content = parse_tool_result(call_result)
                if is_success:
                    result.result_str += translate_mine_block_tool_result(result_content)
                else:
                    result.result_str += f"挖掘失败: {result_content}"
            elif action_type == "enter_mining_mode":
                self.mode = "mining_mode"
                result.result_str = "进入采矿/采掘模式\n"
                return result
            elif action_type == "place_block":
                block = json_obj.get("block")
                x = json_obj.get("x")
                y = json_obj.get("y")
                z = json_obj.get("z")
                
                result_str, args = await self.place_action.place_action(block, x, y, z)            
                result.result_str = result_str

                if not args:
                    return result
                
                call_result = await self.mcp_client.call_tool_directly("place_block", args)
                is_success, result_content = parse_tool_result(call_result)
                result.result_str += translate_place_block_tool_result(result_content,args)

            elif action_type == "chat":
                message = json_obj.get("message")
                args = {"message": message}
                call_result = await self.mcp_client.call_tool_directly("chat", args)
                is_success, result_content = parse_tool_result(call_result)
                if is_success:
                    result.result_str = translate_chat_tool_result(result_content)
                else:
                    result.result_str = f"聊天失败: {result_content}"
            elif action_type == "use_container":
                reason = json_obj.get("reason")
                result.result_str = f"想要使用容器，原因是: {reason}\n"
                self.mode = "container_action"
                return result
            elif action_type == "add_memo":
                memo = json_obj.get("memo")
                result.result_str = f"添加备忘录: {memo}\n"
                self.memo_list.append(memo)
            elif action_type == "remove_memo":
                memo = json_obj.get("memo")
                result.result_str = f"移除备忘录: {memo}\n"
                self.memo_list.remove(memo)
            # 任务动作
            elif action_type == "update_task_list":
                self.mode = "task_action"
                reason = json_obj.get("reason")
                result.result_str = f"选择进行修改任务列表: \n原因: {reason}\n"
                return result
            else:
                self.logger.warning(f"[MaiAgent] {self.mode} 不支持的action_type: {action_type}")
            
        
        return result
    

    def attach_tasks(self, plan_task: asyncio.Task, exec_task: asyncio.Task) -> None:
        """记录由main创建的后台任务以便停止。"""
        self._plan_task = plan_task
        self._exec_task = exec_task

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
                # 等待异步任务结束
                if self._viewer_task and not self._viewer_task.done():
                    try:
                        await asyncio.wait_for(self._viewer_task, timeout=3.0)
                    except asyncio.TimeoutError:
                        self._viewer_task.cancel()
        except Exception:
            pass
        # 取消后台任务
        for task in (self._plan_task, self._exec_task):
            try:
                if task and not task.done():
                    task.cancel()
            except Exception:
                pass

