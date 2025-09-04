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
from agent.environment.environment_updater import global_environment_updater
from agent.block_cache.block_cache import global_block_cache
from agent.prompt_manager.template import init_templates
from agent.action.mine_action import mine_nearby_blocks, mine_block_by_position
from agent.action.move_action import move_to_position
from agent.action.place_action import place_block_action
from agent.utils.utils import (
    convert_mcp_tools_to_openai_format, parse_tool_result, filter_action_tools,
    parse_thinking,
)
from agent.action.craft_action.craft_action import recipe_finder
import traceback
from agent.utils.utils_tool_translation import (
    translate_chat_tool_result
)
from agent.sim_gui.chest import ChestSimGui
from agent.sim_gui.furnace import FurnaceSimGui
from mcp_server.client import global_mcp_client
from agent.thinking_log import global_thinking_log
from agent.mai_mode import mai_mode
from agent.environment.locations import global_location_points
from agent.environment.basic_info import BlockPosition
from view_render.renderer_3d import get_global_renderer_3d

COLOR_MAP = {
    "main_mode": "\033[32m",        # 绿色
    "chat_mode": "\033[38;5;51m",     # 青色
    "task_edit_mode": "\033[38;5;196m", # 红色
    "furnace_gui": "\033[38;5;208m",   # 橙色
    "chest_gui": "\033[38;5;220m",     # 黄色
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
        

        # 初始化状态
        self.initialized = False
        
        self.gui = None
        
        self.chest_list:List[ChestSimGui] = []
        
        
        self.goal_list: list[tuple[str, str, str]] = []  # (goal, status, details)

        self.goal = global_config.game.goal
        
        self.on_going_task_id = ""
        
        
        self.task_done_list: list[tuple[bool, str, str]] = []
        
        self.exec_task: Optional[asyncio.Task] = None
        # 不再需要_viewer_task，因为现在使用线程
        
        # 3D 渲染器实例（需要时启动）
        self.renderer_3d = None
        
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

            if global_config.visual.enable:
                self.start_3d_window_sync()
            
            # 创建并启动环境更新器
            self.environment_updater = global_environment_updater
            self.environment_updater.start()



            await asyncio.sleep(1)
            
            # 初始化NearbyBlockManager
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
    



    async def next_thinking(self) -> TaskResult:
        """
        执行目标
        返回: (执行结果, 执行状态)
        """
        try:            
            # 获取当前环境信息
            await self.environment_updater.perform_update()

            #更新截图
            await self.update_overview()

            input_data = await global_environment.get_all_data()
            
            
            # 根据不同的模式，给予不同的工具
            if mai_mode.mode == "main_mode":
                # 主模式，可以选择基础动作，和深入动作
                prompt = prompt_manager.generate_prompt("main_thinking", **input_data)
                self.logger.info(f" 执行任务提示词: {prompt}")
            elif mai_mode.mode == "task_edit":
                prompt = prompt_manager.generate_prompt("minecraft_excute_task_action", **input_data)
                # self.logger.info(f"\033[38;5;153m 执行任务提示词: {prompt}\033[0m")
            elif mai_mode.mode == "chat":
                prompt = prompt_manager.generate_prompt("chat_mode", **input_data)
                # self.logger.info(f"\033[38;5;208m 执行任务提示词: {prompt}\033[0m")
            else:
                self.logger.warning(f" 不支持的模式: {mai_mode.mode}")
                return
            
            
            thinking = await self.llm_client.simple_chat(prompt)
            # self.logger.info(f" 原始输出: {thinking}")
            
            success, thinking, json_obj, thinking_log = parse_thinking(thinking)
            
            #出现意外的调试
            if not success or not json_obj:
                self.logger.warning(f" 思考结果中没有json对象: {thinking}")
                return TaskResult()
            
            
            
            color_prefix = COLOR_MAP.get(mai_mode.mode, "\033[0m")
            
            if thinking_log:
                global_thinking_log.add_thinking_log(thinking_log,type = "thinking")
                
            self.logger.info(f"{color_prefix} 想法{mai_mode.mode}: {thinking_log}\033[0m")
            
            if json_obj:
                await asyncio.sleep(0.1)
                self.logger.info(f"{color_prefix} 动作: {json_obj}\033[0m")
                global_thinking_log.add_thinking_log(f"执行动作：{json_obj}",type = "action")
                result = await self.excute_action(json_obj)
                global_thinking_log.add_thinking_log(f"执行结果：{result.result_str}",type = "notice")
                
                self.logger.info(f" 执行结果: {result.result_str}")
                
                
        except Exception:
            await asyncio.sleep(1)
            self.logger.error(f" 任务执行异常: {traceback.format_exc()}")
            
        
        
        
    async def excute_action(self,action_json) -> ThinkingJsonResult:
        if mai_mode.mode == "main_mode":
            return await self.excute_main_mode(action_json)
        elif mai_mode.mode == "task_edit":
            return await self.excute_task_edit(action_json)
        elif mai_mode.mode == "chat":
            return await self.excute_chat(action_json)
        elif mai_mode.mode == "furnace_gui":
            # 熔炉GUI模式下的操作由FurnaceSimGui类处理
            return ThinkingJsonResult()
        else:
            self.logger.warning(f" {mai_mode.mode} 不支持的action_type: {action_json.get('action_type')}")
            return ThinkingJsonResult()
        
        
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
            result_str = await move_to_position(x, y, z)
            result.result_str += result_str
            return result
        elif action_type == "break_block":
            type = action_json.get("type")
            digOnly = action_json.get("digOnly",True)
            if type == "nearby":
                name = action_json.get("name")
                count = action_json.get("count")
                success,result_str = await mine_nearby_blocks(name, count, digOnly)
                result.result_str += result_str
                return result
            elif type == "position":
                x = action_json.get("x")
                y = action_json.get("y")
                z = action_json.get("z")
                success,result_str = await mine_block_by_position(x, y, z, digOnly)
                result.result_str += result_str
                return result
            else:
                result.result_str = f"不支持的挖掘类型: {type}，请使用nearby或position\n"
                return result
        elif action_type == "place_block":
            block = action_json.get("block")
            x = action_json.get("x")
            y = action_json.get("y")
            z = action_json.get("z")
            result_str = await place_block_action(block, x, y, z)            
            result.result_str += result_str
        elif action_type == "chat":
            message = action_json.get("message")
            if message is not None:
                message = message.strip().replace('\n', '').replace('\r', '')
            args = {"message": message}
            call_result = await global_mcp_client.call_tool_directly("chat", args)
            is_success, result_content = parse_tool_result(call_result)
            result.result_str += translate_chat_tool_result(result_content)
            return result
        elif action_type == "use_furnace":
            position = action_json.get("position")
            x = math.floor(float(position.get("x")))
            y = math.floor(float(position.get("y")))
            z = math.floor(float(position.get("z")))
            
            block_position = BlockPosition(x = x, y = y, z = z)
            result_str = f"打开熔炉: {x},{y},{z}\n"
            mai_mode.mode = "furnace_gui"
            self.gui = FurnaceSimGui(block_position, self.llm_client)
            use_result = await self.gui.furnace_gui()
            result_str += use_result
            mai_mode.mode = "main_mode"
            result.result_str = result_str
            return result
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
            return result
        elif action_type == "use_chest":
            result_str = ""
            position = action_json.get("position")
            x = math.floor(float(position.get("x")))
            y = math.floor(float(position.get("y")))
            z = math.floor(float(position.get("z")))
            block_position = BlockPosition(x = x, y = y, z = z)
            block = global_block_cache.get_block(x, y, z)
            if block.block_type != "chest":
                result.result_str = f"位置{x},{y},{z}不是箱子，无法使用箱子\n"
                return result
            
            result_str += f"打开箱子: {x},{y},{z}\n"
            mai_mode.mode = "chest_gui"
            self.gui = ChestSimGui(block_position, self.llm_client)
            use_result = await self.gui.chest_gui()
            mai_mode.mode = "main_mode"
            result.result_str += use_result
            return result
            
        elif action_type == "eat":
            item = action_json.get("item")
            result.result_str = f"想要食用: {item}\n"
            args = {"itemName": item, "useType":"consume"} #consume表示食用
            call_result = await global_mcp_client.call_tool_directly("use_item", args)
            is_success, result_content = parse_tool_result(call_result)
            self.logger.info(f"食用结果: {result_content}")
            # result.result_str += translate_eat_tool_result(result_content)
        elif action_type == "use_item":
            item = action_json.get("item")
            entity = action_json.get("entity")
            if entity:
                result.result_str = f"使用: {item}\n"
                args = {"itemName": item,"useType":"activate"} #activate表示激活
            else:
                result.result_str = f"对{entity}使用: {item}\n"
                args = {"itemName": item, "targetEntityName": entity,"useType":"useOn"}
            call_result = await global_mcp_client.call_tool_directly("use_item", args)
            is_success, result_content = parse_tool_result(call_result)
            self.logger.info(f"使用结果: {result_content}")
            # result.result_str += translate_use_item_tool_result(result_content)
        elif action_type == "enter_task_edit_mode":
            mai_mode.mode = "task_edit"
            reason = action_json.get("reason")
            result.result_str = f"选择进行修改任务列表: \n原因: {reason}\n"
            return result
        elif action_type == "set_location":
            name = action_json.get("name")
            info = action_json.get("info")
            position = action_json.get("position")
            x = math.floor(float(position.get("x")))
            y = math.floor(float(position.get("y")))
            z = math.floor(float(position.get("z")))
            
            location_name = global_location_points.add_location(name, info, BlockPosition(x = x, y = y, z = z))
            
            result.result_str = f"设置坐标点: {location_name} {info} {x},{y},{z}\n"
            return result
        else:
            self.logger.warning(f" {mai_mode.mode} 不支持的action_type: {action_type}")
            
            
        return result

    def start_3d_window_sync(self) -> bool:
        """
        同步启动3D渲染窗口。
        - 设置环境变量禁用2D预览，避免与pygame上下文冲突
        - 获取全局3D渲染器并启动
        - 返回是否成功启动
        """
        try:
            self.renderer_3d = get_global_renderer_3d()
            
            if getattr(self.renderer_3d, 'running', False):
                self.logger.info(" 3D渲染器已在运行")
                return True

            ok = self.renderer_3d.start()
            if ok:
                self.logger.info(" 3D渲染窗口启动成功")
                return True
            else:
                self.logger.error(" 3D渲染窗口启动失败")
                return False
        except Exception as e:
            self.logger.error(f" 启动3D渲染窗口失败: {e}")
            return False
        
    async def update_overview(self):
        """更新概览图像"""
        try:
            img_b64 = None
            if self.renderer_3d and getattr(self.renderer_3d, 'running', False):
                # 缩放压缩，降低带宽与内存
                b64 = self.renderer_3d.get_screenshot_base64(scale=0.35)
                if b64:
                    img_b64 = f"data:image/png;base64,{b64}"
                    global_environment.overview_base64 = img_b64
                    
                    self.logger.info(f"更新概览图像: {img_b64[:100]}")
                    await global_environment.get_overview_str()
        except Exception as e:
            self.logger.error(f"update_overview 异常: {e}")

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


    async def shutdown(self) -> None:
        """优雅关闭：停止环境更新器、关闭预览器、取消后台任务。"""
        try:
            if self.environment_updater:
                self.environment_updater.stop()
        except Exception:
            pass
        try:
            if self.renderer_3d:
                self.renderer_3d.stop()
        except Exception:
            pass
        # 取消后台任务
        for task in (self.exec_task):
            try:
                if task and not task.done():
                    task.cancel()
            except Exception:
                pass

