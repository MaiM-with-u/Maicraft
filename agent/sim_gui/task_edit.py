from openai_client.llm_request import LLMClient
from typing import Dict, List, Any
from utils.logger import get_logger
from agent.thinking_log import global_thinking_log
from agent.to_do_list import mai_to_do_list
from agent.environment.environment import global_environment
from agent.environment.environment_updater import global_environment_updater
from agent.prompt_manager.prompt_manager import prompt_manager

logger = get_logger("TaskEditSimGui")


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
        execution_result = await self._parse_and_execute_task_actions(thinking)
        
        # 添加退出标志
        execution_result["should_exit"] = True
        
        return execution_result
    
    async def _parse_and_execute_task_actions(self, thinking: str) -> Dict[str, Any]:
        """
        解析并执行任务编辑动作，支持多个动作，失败时终止执行
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
        task_actions = []
        executed_actions = []
        failed_action = None
        error_message = ""
        success = True
        
        # 结果字段
        new_task_id = ""
        task_id = ""
        done = False
        progress = ""
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
                success = False
                error_message = f"解析动作JSON失败: {e}"
                failed_action = {"raw_json": json_str, "parse_error": str(e)}
                break
        
        # 按顺序执行动作
        if task_actions and success:
            logger.info(f"[TaskEdit] 发现 {len(task_actions)} 个任务编辑动作，开始执行...")
            
            for i, action in enumerate(task_actions):
                try:
                    action_type = action.get("action_type")
                    logger.info(f"[TaskEdit] 执行第 {i+1} 个 {action_type} 动作: {action}")
                    
                    # 执行动作
                    result = await self._execute_task_action(action)
                    
                    # 记录执行结果
                    executed_action = {
                        "action": action,
                        "success": result.get("success", False),
                        "result": result.get("result", ""),
                        "error": result.get("error", "")
                    }
                    executed_actions.append(executed_action)
                    
                    # 更新结果字段
                    if result.get("success"):
                        if "new_task_id" in result:
                            new_task_id = result["new_task_id"]
                        if "task_id" in result:
                            task_id = result["task_id"]
                        if "done" in result:
                            done = result["done"]
                        if "progress" in result:
                            progress = result["progress"]
                        if "result_str" in result:
                            result_parts.append(result["result_str"])
                    
                    # 记录到思考日志
                    if result.get("success"):
                        global_thinking_log.add_thinking_log(f"任务编辑动作 {action_type} 执行成功: {result.get('result', '')}", "action")
                    else:
                        global_thinking_log.add_thinking_log(f"任务编辑动作 {action_type} 执行失败: {result.get('error', '')}", "action")
                    
                    # 如果执行失败，终止后续动作
                    if not result.get("success", False):
                        success = False
                        failed_action = executed_action
                        error_message = result.get("error", "未知错误")
                        logger.error(f"[TaskEdit] 第 {i+1} 个动作执行失败，终止后续动作")
                        break
                    
                    # 等待 0.3 秒（除了最后一个动作）
                    if i < len(task_actions) - 1:
                        await asyncio.sleep(0.3)
                        
                except Exception as e:
                    logger.error(f"[TaskEdit] 执行第 {i+1} 个任务编辑动作时异常: {e}")
                    success = False
                    failed_action = {
                        "action": action,
                        "exception": str(e)
                    }
                    error_message = f"执行动作时发生异常: {e}"
                    break
        
        # 构建最终结果字符串
        final_result_str = "；".join(result_parts) if result_parts else "没有执行任何动作"
        if not success:
            final_result_str += f"；执行失败: {error_message}"
        
        return {
            "success": success,
            "executed_actions": executed_actions,
            "failed_action": failed_action,
            "error_message": error_message,
            "new_task_id": new_task_id,
            "task_id": task_id,
            "done": done,
            "progress": progress,
            "result_str": final_result_str
        }
    
    async def _execute_task_action(self, action_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行单个任务编辑动作
        """
        action_type = action_json.get("action_type")
        
        try:
            if action_type == "change_task":
                new_task_id = action_json.get("new_task_id")
                reason = action_json.get("reason")
                
                if not new_task_id:
                    return {
                        "success": False,
                        "result": "",
                        "error": "缺少new_task_id参数"
                    }
                
                self.on_going_task_id = new_task_id
                return {
                    "success": True,
                    "result_str": f"选择更换到任务: {new_task_id},原因是: {reason}",
                    "error": "",
                    "new_task_id": new_task_id
                }
                
            elif action_type == "update_task_progress":
                progress = action_json.get("progress")
                done = action_json.get("done", False)
                task_id = action_json.get("task_id")
                
                if not task_id:
                    return {
                        "success": False,
                        "result": "",
                        "error": "缺少task_id参数"
                    }
                
                result_data = {
                    "success": True,
                    "error": "",
                    "task_id": task_id,
                    "done": done,
                    "progress": progress
                }
                
                if done:
                    result_data["result_str"] = f"任务({task_id})已完成"
                else:
                    result_data["result_str"] = f"任务({task_id})进度已更新: {progress}"
                
                return result_data
                
            elif action_type == "create_new_task":
                new_task = action_json.get("new_task")
                new_task_criteria = action_json.get("new_task_criteria")
                
                if not new_task:
                    return {
                        "success": False,
                        "result": "",
                        "error": "缺少new_task参数"
                    }
                
                # 使用全局的 mai_to_do_list
                mai_to_do_list.add_task(new_task, new_task_criteria)
                
                return {
                    "success": True,
                    "result_str": f"创建新任务: {new_task},原因: {new_task_criteria}",
                    "error": ""
                }
                
                  
            else:
                return {
                    "success": False,
                    "result": "",
                    "error": f"不支持的任务编辑动作类型: {action_type}"
                }
                
        except Exception as e:
            logger.error(f"[TaskEdit] 执行任务编辑动作时发生异常: {e}")
            return {
                "success": False,
                "result": "",
                "error": f"执行异常: {e}"
            }