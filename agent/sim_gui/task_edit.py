from openai_client.llm_request import LLMClient
from typing import Dict, List, Any
from utils.logger import get_logger
from agent.thinking_log import global_thinking_log
from agent.to_do_list import mai_to_do_list
from agent.environment.environment import global_environment
from agent.environment.environment_updater import global_environment_updater
from agent.prompt_manager.prompt_manager import prompt_manager
import asyncio
import json
from json_repair import repair_json

logger = get_logger("\033[38;5;201m TaskEdit\033[0m")


class TaskEditSimGui:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.on_going_task_id = ""
    
    async def task_edit_gui(self, reason: str = "", on_going_task_id: str = "") -> Dict[str, Any]:
        """
        执行任务编辑界面
        返回: {
            "success": bool,
            "executed_actions": List[Dict],
            "failed_action": Dict,
            "error_message": str,
            "has_exit_action": bool,
            "new_task_id": str,
            "task_id": str,
            "done": bool,
            "progress": str,
            "result_str": str,
            "should_exit": bool  # 是否应该退出任务编辑模式
        }
        """
        self.on_going_task_id = on_going_task_id
        
        # 更新环境信息
        await global_environment_updater.perform_update()
        input_data = await global_environment.get_all_data()
        
        # 生成任务编辑提示词
        prompt = prompt_manager.generate_prompt("minecraft_excute_task_action", **input_data)
        
        # 让LLM思考任务编辑
        thinking = await self.llm_client.simple_chat(prompt)
        
        logger.info(f"任务编辑提示词: {prompt}")
        logger.info(f"任务编辑思考结果: {thinking}")
        
        # 解析并执行多个任务编辑动作
        final_result_str = await self._parse_and_execute_task_actions(thinking)
        
        return final_result_str
    
    async def _parse_and_execute_task_actions(self, thinking: str) -> Dict[str, Any]:
        """
        解析并执行任务编辑动作，支持多个动作，失败时终止执行
        """
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
        task_actions = []
        
        result_parts = []
        
        # 解析所有任务动作
        for json_str, start, end in json_objects:
            try:
                repaired_json = repair_json(json_str)
                json_obj = json.loads(repaired_json)
                action_type = json_obj.get("action_type")
                
                if action_type in ["change_task", "update_task_progress", "create_new_task"]:
                    task_actions.append(json_obj)
                        
            except Exception as e:
                logger.error(f"[TaskEdit] 解析动作JSON时异常: {json_str}, 错误: {e}")
                break
        
        # 按顺序执行动作
        if task_actions:
            
            for i, action in enumerate(task_actions):
                try:
                    action_type = action.get("action_type")
                    logger.info(f"[TaskEdit] 执行第 {i+1} 个 {action_type} 动作: {action}")
                    
                    # 执行动作
                    success, result_str = await self._execute_task_action(action)
                    
                    result_parts.append(result_str)
                    # 如果执行失败，终止后续动作
                    if not success:
                        logger.error(f"[TaskEdit] 第 {i+1} 个动作执行失败，终止后续动作")
                        break
                    
                    # 等待 0.3 秒（除了最后一个动作）
                    if i < len(task_actions) - 1:
                        await asyncio.sleep(0.3)
                        
                except Exception as e:
                    logger.error(f"[TaskEdit] 执行第 {i+1} 个任务编辑动作时异常: {e}")
                    break
        
        # 构建最终结果字符串
        final_result_str = "；".join(result_parts) if result_parts else "没有执行任何动作"
        
        return final_result_str
    
    async def _execute_task_action(self, action_json: Dict[str, Any]) -> tuple[bool,str]:
        """
        执行单个任务编辑动作
        """
        action_type = action_json.get("action_type")
        
        try:
            if action_type == "change_task":
                task_id = action_json.get("task_id")
                
                if not task_id:
                    return False, "缺少task_id参数或参数不正确"
                
                self.on_going_task_id = task_id
                return True, f"选择更换到任务: {task_id}"
                
            elif action_type == "update_task_progress":
                progress = action_json.get("progress")
                done = action_json.get("done", False)
                task_id = action_json.get("task_id")
                
                if not task_id:
                    return False, "缺少task_id参数或参数不正确"
                
                # 实际更新任务状态
                if done:
                    mai_to_do_list.mark_task_done(task_id)
                    return True, f"任务({task_id})已完成"
                else:
                    mai_to_do_list.update_task_progress(task_id, progress)
                    return True, f"任务({task_id})进度已更新: {progress}"
                
                  
            elif action_type == "create_new_task":
                new_task_details = action_json.get("new_task_details")
                new_task_criteria = action_json.get("new_task_criteria")
                
                if not new_task_details:
                    return False, "缺少new_task_details参数或参数不正确"
                
                # 使用全局的 mai_to_do_list
                mai_to_do_list.add_task(new_task_details, new_task_criteria)
                
                return True, f"创建新任务: {new_task_details},评估标准: {new_task_criteria}"
                
                  
            else:
                return False, f"不支持的任务编辑动作类型: {action_type}"
                
        except Exception as e:
            logger.error(f"[TaskEdit] 执行任务编辑动作时发生异常: {e}")
            return False, f"执行异常: {e}"