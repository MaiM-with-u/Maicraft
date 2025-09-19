import asyncio
import math
from typing import List, Any, Optional, Dict, Tuple, Callable
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
from agent.action.mine_action import mine_nearby_blocks, mine_block_by_position, mine_in_direction
from agent.action.move_action import move_to_position
from agent.action.place_action import place_block_action
from agent.utils.utils import (
    convert_mcp_tools_to_openai_format, parse_tool_result, filter_action_tools,
    parse_thinking, parse_thinking_multiple,
)
from agent.action.craft_action.craft_action import recipe_finder
from agent.action.find_action import find_block_action
import traceback
from agent.utils.utils_tool_translation import (
    translate_chat_tool_result
)
from agent.sim_gui.chest import ChestSimGui
from agent.sim_gui.furnace import FurnaceSimGui
from agent.sim_gui.task_edit import TaskEditSimGui
from agent.container_cache.container_cache import global_container_cache
from mcp_server.client import global_mcp_client
from agent.thinking_log import global_thinking_log
from agent.mai_mode import mai_mode
from agent.environment.locations import global_location_points
from agent.common.basic_class import BlockPosition
from view_render.renderer_3d import get_global_renderer_3d
from mcp_server.client import Tool
from agent.environment.movement import global_movement
from agent.events import global_event_emitter, ListenerHandle

COLOR_MAP = {
    "move": "\033[32m",        # 绿色
    "break_block": "\033[38;5;196m",  # 红色
    "place_block": "\033[38;5;208m",  # 橙色
    "chat": "\033[38;5;51m",     # 青色
    "use_furnace": "\033[38;5;220m",  # 黄色
    "craft": "\033[38;5;135m",   # 紫色
    "use_chest": "\033[38;5;220m",   # 黄色
    "eat": "\033[38;5;46m",      # 亮绿色
    "use_item": "\033[38;5;226m",    # 亮黄色
    "edit_task_list": "\033[38;5;201m", # 粉色
    "set_location": "\033[38;5;129m",  # 深紫色
}



class ThinkingJsonResult:
    def __init__(self):
        self.success = True
        self.result_str = ""
        

class MaiAgent:
    def __init__(self):
        self.logger = get_logger("MaiAgent")

        # 初始化LLM客户端
        self.llm_client: Optional[LLMClient] = None
        self.llm_client_fast: Optional[LLMClient] = None
        

        # 初始化LLM和工具适配器
        # 延迟初始化
        self.tools: Optional[List[Tool]] = None


        # 初始化状态
        self.initialized = False
        
        self.gui = None
        
        self.chest_list:List[ChestSimGui] = []
        
        
        self.goal_list: list[tuple[str, str, str]] = []  # (goal, status, details)

        self.goal = global_config.game.goal
        self.complete_goal = False
        
        self.on_going_task_id = ""
        
        self.task_done_list: list[tuple[bool, str, str]] = []
        
        self.exec_task: Optional[asyncio.Task] = None
        # 不再需要_viewer_task，因为现在使用线程
        
        # 3D 渲染器实例（需要时启动）
        self.renderer_3d = None
        
        # 动作中断状态（现在使用global_movement的中断事件）
        self.current_action_task: Optional[asyncio.Task] = None

        # 跟踪管理的监听器句柄
        self._listener_handles: List[ListenerHandle] = []
    
            
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
            
            
            self.tools = await global_mcp_client.get_tools_metadata()
            self.action_tools = filter_action_tools(self.tools)
            self.openai_tools = convert_mcp_tools_to_openai_format(self.action_tools)

            if global_config.visual.enable:
                self.start_3d_window_sync()
            
            # 创建并启动环境更新器
            global_environment_updater.start()

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
        
        
        i = 0
        while not self.complete_goal:
            await self.next_thinking()
            i += 1
            if i % 5 == 0:
                await self.judge_task()
    

    async def judge_task(self):
        """
        评估任务
        """
        try:
            input_data = await global_environment.get_all_data()
            prompt = prompt_manager.generate_prompt("judge", **input_data)
            thinking = await self.llm_client.simple_chat(prompt)

            if thinking:
                global_thinking_log.set_judge_guidance(judge_guidance=thinking)
                global_thinking_log.clear_thinking_log()
        except Exception:
            await asyncio.sleep(1)
            self.logger.error(f" 任务评估异常: {traceback.format_exc()}")


    async def next_thinking(self):
        """
        执行目标
        返回: (执行结果, 执行状态)
        """
        try:
            # 获取当前环境信息
            # await global_environment_updater.perform_update()

            #更新截图
            await self.update_overview()

            input_data = await global_environment.get_all_data()
            

            prompt = prompt_manager.generate_prompt("main_thinking", **input_data)
            self.logger.info(f" 思考提示词: {prompt}")
            
            self.logger.info(" 开始调用LLM...")
            thinking = await self.llm_client.simple_chat(prompt)
            self.logger.info(f" LLM调用完成，原始输出: {thinking}")
            
            self.logger.info(" 开始解析思考结果...")
            
            # 尝试解析多个JSON动作
            success, thinking, json_objects, thinking_log = parse_thinking_multiple(thinking)
            
            #出现意外的调试
            if not success or not json_objects:
                self.logger.warning(f" 思考结果中没有json对象: {thinking}")
                return 
            
            if thinking_log:
                global_thinking_log.add_thinking_log(thinking_log,type = "thinking")
                
            self.logger.info(f" 想法: {thinking_log}")
            
            # 执行多个动作
            if json_objects:
                # self.logger.info(f" 检测到 {len(json_objects)} 个动作需要执行")
                
                for i, json_obj in enumerate(json_objects):
                    action_type = json_obj.get("action_type", "unknown")
                    action_color = COLOR_MAP.get(action_type, "\033[0m")
                    
                    self.logger.info(f"{action_color} 动作 {i+1}/{len(json_objects)}: {json_obj}\033[0m")
                    await asyncio.sleep(0.1)
                    
                    result = await self.excute_main_mode(json_obj)
                    global_thinking_log.add_thinking_log(f"执行动作 {i+1}/{len(json_objects)}：{json_obj};{result.result_str}\n",type = "action")
                    
                    self.logger.info(f"{action_color} 执行结果 {i+1}/{len(json_objects)}: {result.result_str}\033[0m")
                    
                    # 检查动作是否失败，如果失败则停止后续动作
                    if not result.success or "失败" in result.result_str or "错误" in result.result_str or "无法" in result.result_str:
                        self.logger.warning(f" 动作 {i+1} 执行失败，停止后续动作执行")
                        break
                
                
        except Exception:
            await asyncio.sleep(1)
            self.logger.error(f" 任务执行异常: {traceback.format_exc()}")
        
        
        
    async def excute_main_mode(self,action_json) -> ThinkingJsonResult:
        result = ThinkingJsonResult()
        
        # 检查中断状态
        if global_movement.interrupt_flag:
            interrupt_reason = global_movement.interrupt_reason
            global_movement.clear_interrupt()
            result.result_str = f"动作被中断：{interrupt_reason}"
            result.success = False
            return result
            
        action_type = action_json.get("action_type")
        if action_type == "move":
            position = action_json.get("position", {})
            x = math.floor(float(position.get("x", 0)))
            y = math.floor(float(position.get("y", 0)))
            z = math.floor(float(position.get("z", 0)))
            success, result_str = await move_to_position(x, y, z)
            result.success = success
            result.result_str += result_str
            return result
        elif action_type == "mine_block":
            # type = action_json.get("type","nearby")
            digOnly = action_json.get("digOnly",False)
            # if type == "nearby":
            name = action_json.get("name")
            count = action_json.get("count")
            success,result_str = await mine_nearby_blocks(name, count, digOnly)
            result.success = success
            result.result_str += result_str
            # 破坏方块后清理不存在的容器（附近可能被破坏的容器）
            current_pos = global_environment.block_position
            global_container_cache.clean_invalid_containers(current_pos)
            return result
        elif action_type == "mine_block_by_position":
            x = action_json.get("x")
            y = action_json.get("y")
            z = action_json.get("z")
            digOnly = action_json.get("digOnly",False)
            success,result_str = await mine_block_by_position(x, y, z, digOnly)
            result.success = success
            result.result_str += result_str
            # 破坏方块后清理不存在的容器（指定位置）
            block_pos = BlockPosition(x=x, y=y, z=z)
            global_container_cache.clean_invalid_containers(block_pos)
            return result
        elif action_type == "mine_in_direction":
            direction = action_json.get("direction")
            timeout = action_json.get("timeout")
            digOnly = action_json.get("digOnly",False)
            success,result_str = await mine_in_direction(direction, timeout, digOnly)
            result.success = success
            result.result_str += result_str
            return result
        elif action_type == "place_block":
            block = action_json.get("block")
            x = action_json.get("x")
            y = action_json.get("y")
            z = action_json.get("z")
            success, result_str = await place_block_action(block, x, y, z)            
            result.success = success
            result.result_str += result_str
        elif action_type == "find_block":
            block = action_json.get("block")
            radius = action_json.get("radius", 16.0)  # 默认搜索半径16格
            
            success, result_str = await find_block_action(block, radius)
            result.success = success
            result.result_str += result_str
            return result
        elif action_type == "use_furnace":
            position = action_json.get("position")
            x = math.floor(float(position.get("x")))
            y = math.floor(float(position.get("y")))
            z = math.floor(float(position.get("z")))
            
            block_position = BlockPosition(x = x, y = y, z = z)
            
            # 验证熔炉是否实际存在
            if not global_container_cache.verify_container_exists(block_position, "furnace"):
                result.result_str = f"位置 {x},{y},{z} 没有熔炉，无法使用熔炉\n"
                # 清理该位置可能存在的不正确缓存记录
                global_container_cache.clean_invalid_containers(block_position)
                return result
            
            # 添加熔炉到缓存
            global_container_cache.add_container(block_position, "furnace")
            
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
            result.result_str = f"合成: {item} 数量: {count}\n"
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
            
            # 验证箱子是否实际存在
            if not global_container_cache.verify_container_exists(block_position, "chest"):
                result.result_str = f"位置{x},{y},{z}没有箱子，无法使用箱子\n"
                # 清理该位置可能存在的不正确缓存记录
                global_container_cache.clean_invalid_containers(block_position)
                return result
            
            # 添加箱子到缓存
            global_container_cache.add_container(block_position, "chest")
            
            result_str += f"打开箱子: {x},{y},{z}\n"
            mai_mode.mode = "chest_gui"
            self.gui = ChestSimGui(block_position, self.llm_client)
            use_result = await self.gui.chest_gui()
            mai_mode.mode = "main_mode"
            result.result_str += use_result
            return result
        elif action_type == "toss_item":
            item = action_json.get("item")
            count = action_json.get("count")
            args = {"type":"toss","item": item, "count": count}
            call_result = await global_mcp_client.call_tool_directly("basic_control", args)
            is_success, result_content = parse_tool_result(call_result)
            self.logger.info(f"丢弃结果: {result_content}")
            result.success = is_success
            if isinstance(result_content, str):
                result.result_str += result_content
            else:
                result.result_str += f"丢弃了{item} x {count}"
            return result
            
        elif action_type == "eat":
            item = action_json.get("item")
            result.result_str = f""
            args = {"itemName": item, "useType":"consume"} #consume表示食用
            call_result = await global_mcp_client.call_tool_directly("use_item", args)
            is_success, result_content = parse_tool_result(call_result)
            self.logger.info(f"食用结果: {result_content}")
            result.success = is_success
            if isinstance(result_content, dict):
                result.result_str += f"食用了{result_content.get('itemName')}"
            else:
                result.result_str += str(result_content)
        elif action_type == "kill_mob":
            entity = action_json.get("entity")
            timeout = action_json.get("timeout")
            result.result_str = f"杀死{entity}，超时时间：{timeout}秒\n"
            args = {"mob": entity, "timeout": timeout}
            call_result = await global_mcp_client.call_tool_directly("kill_mob", args)
            is_success, result_content = parse_tool_result(call_result)
            
            self.logger.info(f"杀死结果: {result_content}")
            
            result.success = is_success
            if is_success:
                result.result_str += f"杀死了{entity}"
            else:
                result.result_str += str(result_content)
                
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
            result.success = is_success
            if isinstance(result_content, str):
                result.result_str += result_content
            else:
                result.result_str += f"使用{result_content.get('itemName')}"
            
        elif action_type == "edit_task_list":
            reason = action_json.get("reason")
            
            # 创建任务编辑处理器并执行
            task_edit_gui = TaskEditSimGui(self.llm_client)
            execution_result = await task_edit_gui.task_edit_gui(reason, self.on_going_task_id)
            
            # 添加执行结果
            result.result_str += execution_result
            return result
        elif action_type == "set_location":
            name = action_json.get("name")
            info = action_json.get("info")
            position = action_json.get("position")
            type = action_json.get("type")
            
            # 只有需要位置信息的操作才解析坐标
            if type in ["set", "delete"] and position is not None:
                x = math.floor(float(position.get("x")))
                y = math.floor(float(position.get("y")))
                z = math.floor(float(position.get("z")))
                
                if type == "set":
                    location_name = global_location_points.add_location(name, info, BlockPosition(x = x, y = y, z = z))
                    result.result_str = f"设置坐标点: {location_name} {info} {x},{y},{z}\n"
                elif type == "delete":
                    global_location_points.remove_location(name = name, position=BlockPosition(x = x, y = y, z = z))
                    location_name = name
                    result.result_str = f"删除坐标点: {location_name} {info} {x},{y},{z}\n"
            elif type == "delete" and position is None:
                # 如果没有提供位置，只按名称删除
                global_location_points.remove_location(name = name)
                location_name = name
                result.result_str = f"删除坐标点: {location_name}\n"
            elif type == "update":
                global_location_points.edit_location(name = name, info = info)
                location_name = name
                result.result_str = f"更新坐标点: {location_name} {info}\n"
            
            return result
        elif action_type == "complete_goal":
            self.complete_goal = True
            result.result_str = "目标已经完成，目标条件已经达成\n"
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

    async def start(self) -> None:
        """启动执行循环"""
        # 启动两个主循环
        # plan_task = asyncio.create_task(agent.run_plan_loop())
        self.exec_task = asyncio.create_task(self.run_execute_loop())
        
    def on(self, event_type: str, callback: Callable) -> ListenerHandle:
        """
        注册持续事件监听器

        Args:
            event_type: 事件类型 (如 'chat', 'playerJoined', 'entityHurt')
            callback: 回调函数，签名: async def callback(event: BaseEvent) -> None

        Returns:
            ListenerHandle: 监听器句柄，用于后续管理

        Example:
            @bot.on('chat')
            async def on_chat(event):
                message = event.data.message
                username = event.data.username
                print(f"{username}: {message}")
        """
        handle = global_event_emitter.on(event_type, callback)
        self._listener_handles.append(handle)
        return handle

    def once(self, event_type: str, callback: Callable) -> ListenerHandle:
        """
        注册一次性事件监听器

        Args:
            event_type: 事件类型
            callback: 回调函数，执行一次后自动移除

        Returns:
            ListenerHandle: 监听器句柄

        Example:
            @bot.once('playerJoined')
            async def welcome_new_player(event):
                username = event.data.username
                await bot.chat(f"欢迎 {username} 加入游戏！")
        """
        handle = global_event_emitter.once(event_type, callback)
        self._listener_handles.append(handle)
        return handle

    def off(self, event_type: str, callback: Optional[Callable] = None) -> bool:
        """
        移除事件监听器

        Args:
            event_type: 事件类型
            callback: 要移除的回调函数，如果为None则移除该类型的所有监听器

        Returns:
            bool: 是否成功移除

        Example:
            bot.off('chat', my_chat_handler)  # 移除特定监听器
            bot.off('chat')  # 移除所有聊天监听器
        """
        return global_event_emitter.off(event_type, callback)

    def remove_all_listeners(self, event_type: Optional[str] = None) -> int:
        """
        移除所有监听器

        Args:
            event_type: 事件类型，如果为None则移除所有类型的监听器

        Returns:
            int: 移除的监听器数量
        """
        return global_event_emitter.remove_all_listeners(event_type)

    def get_listener_count(self, event_type: str) -> int:
        """获取指定事件类型的监听器数量"""
        return global_event_emitter.listener_count(event_type)

    def get_event_types(self) -> List[str]:
        """获取所有已注册监听器的事件类型"""
        return global_event_emitter.event_names()

    async def shutdown(self) -> None:
        """优雅关闭：停止环境更新器、关闭预览器、取消后台任务、清理监听器。"""
        try:
            if global_environment_updater:
                global_environment_updater.stop()
        except Exception:
            pass
        try:
            if self.renderer_3d:
                self.renderer_3d.stop()
        except Exception:
            pass

        # 清理监听器
        for handle in self._listener_handles:
            if not handle.is_removed:
                handle.remove()
        self._listener_handles.clear()

        # 取消后台任务
        if self.exec_task and not self.exec_task.done():
            try:
                self.exec_task.cancel()
            except Exception:
                pass

