#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码运行器 - 用于运行解析出来的Python代码并返回结果
"""

import io
import asyncio
import traceback
import os
import json
import importlib.util
from typing import Dict, Any
from contextlib import redirect_stdout, redirect_stderr
from agent.fixed_actions.action_bot import bot
from agent.smart_craft.craft_action import Item
from agent.block_cache.block_cache import Block
from agent.environment.basic_info import BlockPosition, Position


class CodeRunner:
    """代码运行器类"""
    
    def __init__(self):
        self.bot = bot  # 预导入的bot对象
        self.learnt_functions = {}  # 存储学到的函数
        self._load_learnt_functions()
    
    def _load_learnt_functions(self):
        """动态加载学到的动作函数"""
        try:
            # 获取 learnt_actions 目录路径
            learnt_actions_dir = os.path.join(os.path.dirname(__file__), "learnt_actions")
            actions_json_path = os.path.join(learnt_actions_dir, "all_learnt_actions.json")
            
            if not os.path.exists(actions_json_path):
                return
            
            # 读取 all_learnt_actions.json
            with open(actions_json_path, "r", encoding="utf-8") as f:
                actions_data = json.load(f)
            
            # 遍历每个动作记录
            for action_record in actions_data:
                if not isinstance(action_record, dict):
                    continue
                
                name = action_record.get("name", "")
                if not name or "/" not in name:
                    continue
                
                # 解析文件名和函数名 (格式: "filename.py/function_name")
                filename, function_name = name.split("/", 1)
                if not filename.endswith(".py"):
                    continue
                
                # 构建文件路径
                file_path = os.path.join(learnt_actions_dir, filename)
                if not os.path.exists(file_path):
                    continue
                
                try:
                    # 动态导入模块
                    spec = importlib.util.spec_from_file_location(function_name, file_path)
                    if spec is None or spec.loader is None:
                        continue
                    
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # 获取函数对象
                    if hasattr(module, function_name):
                        function_obj = getattr(module, function_name)
                        if callable(function_obj):
                            self.learnt_functions[function_name] = function_obj
                            
                except Exception:
                    # 导入失败时静默跳过
                    continue
                    
        except Exception:
            # 加载失败时静默跳过
            pass
    
    def reload_learnt_functions(self):
        """重新加载学到的函数"""
        old_functions = set(self.learnt_functions.keys())
        self.learnt_functions.clear()
        self._load_learnt_functions()
        new_functions = set(self.learnt_functions.keys())
        
        # 打印加载的函数信息（用于调试）
        if new_functions:
            print(f"[CodeRunner] 已加载学到的函数: {list(new_functions)}")
        if new_functions != old_functions:
            added = new_functions - old_functions
            removed = old_functions - new_functions
            if added:
                print(f"[CodeRunner] 新增函数: {list(added)}")
            if removed:
                print(f"[CodeRunner] 移除函数: {list(removed)}")
    
    def get_learnt_functions(self):
        """获取已加载的学到的函数列表"""
        return list(self.learnt_functions.keys())
        
    def run_code(self, code: str) -> Dict[str, Any]:
        """
        运行Python代码并返回结果
        会自动检测并执行代码中定义的函数
        
        Args:
            code: 要运行的Python代码字符串
            
        Returns:
            包含执行结果的字典，格式如下：
            {
                "success": bool,  # 是否执行成功
                "output": str,    # 标准输出内容
                "error": str,     # 错误信息（如果有）
                "result": Any,    # 代码的返回值（如果有）
                "traceback": str  # 完整的错误堆栈（如果有）
            }
        """
        if not code or not code.strip():
            return {
                "success": False,
                "output": "",
                "error": "代码为空",
                "result": None,
                "traceback": ""
            }
        
        # 每次执行前重新加载学到的函数，确保获取最新的函数
        self.reload_learnt_functions()
        
        # 创建新的命名空间，预导入bot对象
        namespace = {
            "__builtins__": __builtins__,
            "bot": self.bot,
            # 预导入的类型，供执行代码直接使用
            "Item": Item,
            "Block": Block,
            "BlockPosition": BlockPosition,
            "Position": Position,
            # 注入 asyncio 相关
            "asyncio": asyncio,
            "sleep": asyncio.sleep,
            "print": print,
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "set": set,
            "bool": bool,
            "type": type,
            "isinstance": isinstance,
            "hasattr": hasattr,
            "getattr": getattr,
            "setattr": setattr,
            "dir": dir,
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
            "sum": sum,
            "max": max,
            "min": min,
            "abs": abs,
            "round": round,
            "sorted": sorted,
            "reversed": reversed,
            "any": any,
            "all": all,
        }
        
        # 注入学到的函数
        namespace.update(self.learnt_functions)
        
        # 捕获标准输出和错误输出
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # 运行前同步并打印一次背包信息
                try:
                    inv = getattr(self.bot, 'inventory', None)
                    inv_len = len(inv) if hasattr(inv, '__len__') else 'N/A'
                    preview = inv[:3] if isinstance(inv, list) else inv
                    print(f"[预检] inventory_len={inv_len}, preview={preview}")
                except Exception:
                    print("[预检] 同步/读取 bot.inventory 失败")
                # 执行代码（定义函数等）
                exec(code, namespace)
                
                # 检测并执行定义的函数
                function_results = self._execute_functions(namespace)
                
            # 获取输出
            output = stdout_capture.getvalue()
            error_output = stderr_capture.getvalue()
            
            # 如果有函数执行结果，添加到输出中
            if function_results:
                output += "\n" + function_results
            
            # 检查是否有错误输出
            if error_output:
                return {
                    "success": False,
                    "output": output,
                    "error": error_output,
                    "result": None,
                    "traceback": ""
                }
            
            return {
                "success": True,
                "output": output,
                "error": "",
                "result": None,
                "traceback": ""
            }
            
        except Exception as e:
            # 捕获执行异常
            error_msg = str(e)
            tb = traceback.format_exc()
            
            return {
                "success": False,
                "output": stdout_capture.getvalue(),
                "error": error_msg,
                "result": None,
                "traceback": tb
            }
    
    def _execute_functions(self, namespace: Dict[str, Any]) -> str:
        """
        检测并执行命名空间中定义的函数
        
        Args:
            namespace: 执行代码后的命名空间
            
        Returns:
            函数执行结果的字符串
        """
        import inspect
        
        results = []
        
        # 遍历命名空间中的所有对象
        for name, obj in namespace.items():
            # 跳过内置对象和预导入的对象
            if name.startswith('__') or name in ['bot', 'print', 'len', 'str', 'int', 'float', 
                                                'list', 'dict', 'tuple', 'set', 'bool', 'type',
                                                'isinstance', 'hasattr', 'getattr', 'setattr',
                                                'dir', 'range', 'enumerate', 'zip', 'map',
                                                'filter', 'sum', 'max', 'min', 'abs', 'round',
                                                'sorted', 'reversed', 'any', 'all', 'asyncio', 'sleep']:
                continue
                
            # 检查是否是函数
            if callable(obj) and inspect.isfunction(obj):
                # 跳过学到的异步函数，它们应该在异步环境中执行
                if name in self.learnt_functions:
                    results.append(f"跳过学到的异步函数 {name}（将在异步环境中执行）")
                    continue
                    
                try:
                    # 检查函数参数
                    sig = inspect.signature(obj)
                    params = list(sig.parameters.keys())
                    
                    # 如果函数没有参数，直接执行
                    if not params:
                        result = obj()
                        results.append(f"执行函数 {name}(): {result}")
                    # 如果函数只有一个参数且是bot，传入bot对象
                    elif len(params) == 1 and params[0] in ['bot', 'self']:
                        result = obj(self.bot)
                        results.append(f"执行函数 {name}(bot): {result}")
                    # 如果函数有默认参数，尝试用默认值调用
                    elif any(param.default != inspect.Parameter.empty for param in sig.parameters.values()):
                        # 构建默认参数
                        kwargs = {}
                        for param_name, param in sig.parameters.items():
                            if param.default != inspect.Parameter.empty:
                                kwargs[param_name] = param.default
                        result = obj(**kwargs)
                        results.append(f"执行函数 {name}(默认参数): {result}")
                    else:
                        # 其他情况，尝试无参数调用（可能会失败）
                        try:
                            result = obj()
                            results.append(f"执行函数 {name}(): {result}")
                        except TypeError:
                            results.append(f"跳过函数 {name}（需要参数但无法自动提供）")
                            
                except Exception as e:
                    results.append(f"执行函数 {name} 时出错: {str(e)}")
        
        return "\n".join(results) if results else ""
    
    def run_code_with_return(self, code: str) -> Dict[str, Any]:
        """
        运行Python代码并尝试获取返回值
        
        Args:
            code: 要运行的Python代码字符串
            
        Returns:
            包含执行结果的字典
        """
        if not code or not code.strip():
            return {
                "success": False,
                "output": "",
                "error": "代码为空",
                "result": None,
                "traceback": ""
            }
        
        # 每次执行前重新加载学到的函数，确保获取最新的函数
        self.reload_learnt_functions()
        
        # 创建新的命名空间
        namespace = {
            "__builtins__": __builtins__,
            "bot": self.bot,
            # 预导入的类型，供执行代码直接使用
            "Item": Item,
            "Block": Block,
            "BlockPosition": BlockPosition,
            "Position": Position,
            # 注入 asyncio 相关
            "asyncio": asyncio,
            "sleep": asyncio.sleep,
            "print": print,
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "set": set,
            "bool": bool,
            "type": type,
            "isinstance": isinstance,
            "hasattr": hasattr,
            "getattr": getattr,
            "setattr": setattr,
            "dir": dir,
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
            "sum": sum,
            "max": max,
            "min": min,
            "abs": abs,
            "round": round,
            "sorted": sorted,
            "reversed": reversed,
            "any": any,
            "all": all,
        }
        
        # 注入学到的函数
        namespace.update(self.learnt_functions)
        
        # 捕获标准输出和错误输出
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # 执行代码并尝试获取返回值
                if code.strip().startswith('return '):
                    # 如果代码以return开头，包装成函数
                    wrapped_code = f"def _temp_func():\n    {code}\n    return None\nresult = _temp_func()"
                else:
                    # 普通代码执行
                    wrapped_code = code
                
                exec(wrapped_code, namespace)
                
                # 尝试获取result变量
                result = namespace.get('result', None)
                
            # 获取输出
            output = stdout_capture.getvalue()
            error_output = stderr_capture.getvalue()
            
            # 检查是否有错误输出
            if error_output:
                return {
                    "success": False,
                    "output": output,
                    "error": error_output,
                    "result": result,
                    "traceback": ""
                }
            
            return {
                "success": True,
                "output": output,
                "error": "",
                "result": result,
                "traceback": ""
            }
            
        except Exception as e:
            # 捕获执行异常
            error_msg = str(e)
            tb = traceback.format_exc()
            
            return {
                "success": False,
                "output": stdout_capture.getvalue(),
                "error": error_msg,
                "result": None,
                "traceback": tb
            }

    async def run_code_async(self, code: str) -> Dict[str, Any]:
        """
        异步运行Python代码并返回结果，自动检测并执行定义的同步/异步函数
        """
        if not code or not code.strip():
            return {
                "success": False,
                "output": "",
                "error": "代码为空",
                "result": None,
                "traceback": ""
            }
        
        # 每次执行前重新加载学到的函数，确保获取最新的函数
        self.reload_learnt_functions()

        namespace = {
            "__builtins__": __builtins__,
            "bot": self.bot,
            # 预导入的类型，供执行代码直接使用
            "Item": Item,
            "Block": Block,
            "BlockPosition": BlockPosition,
            "Position": Position,
            # 注入 asyncio 相关
            "asyncio": asyncio,
            "sleep": asyncio.sleep,
            "print": print,
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "set": set,
            "bool": bool,
            "type": type,
            "isinstance": isinstance,
            "hasattr": hasattr,
            "getattr": getattr,
            "setattr": setattr,
            "dir": dir,
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
            "sum": sum,
            "max": max,
            "min": min,
            "abs": abs,
            "round": round,
            "sorted": sorted,
            "reversed": reversed,
            "any": any,
            "all": all,
        }
        
        # 注入学到的函数
        namespace.update(self.learnt_functions)

        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            from contextlib import redirect_stdout, redirect_stderr
            import inspect
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # 先执行代码以便定义函数
                exec(code, namespace)

                # 执行同步与异步函数
                function_results = []
                function_error_lines = []
                
                # 学到的函数只作为工具函数提供，不自动执行
                # 它们会在代码中被显式调用时才执行
                
                # 然后执行其他定义的函数
                for name, obj in list(namespace.items()):
                    if name.startswith('__') or name in ['bot', 'print', 'len', 'str', 'int', 'float',
                                                         'list', 'dict', 'tuple', 'set', 'bool', 'type',
                                                         'isinstance', 'hasattr', 'getattr', 'setattr',
                                                         'dir', 'range', 'enumerate', 'zip', 'map',
                                                         'filter', 'sum', 'max', 'min', 'abs', 'round',
                                                         'sorted', 'reversed', 'any', 'all', 'asyncio', 'sleep']:
                        continue
                    
                    # 跳过学到的函数，已经处理过了
                    if name in self.learnt_functions:
                        continue

                    if callable(obj) and inspect.isfunction(obj):
                        try:
                            sig = inspect.signature(obj)
                            params = list(sig.parameters.keys())
                            if inspect.iscoroutinefunction(obj):
                                # 异步函数
                                if not params:
                                    r = await obj()
                                    function_results.append(f"执行异步函数 {name}(): {r}")
                                elif len(params) == 1 and params[0] in ['bot', 'self']:
                                    r = await obj(self.bot)
                                    function_results.append(f"执行异步函数 {name}(bot): {r}")
                                else:
                                    function_results.append(f"跳过异步函数 {name}（需要参数但无法自动提供）")
                            else:
                                # 同步函数
                                if not params:
                                    r = obj()
                                    function_results.append(f"执行函数 {name}(): {r}")
                                elif len(params) == 1 and params[0] in ['bot', 'self']:
                                    r = obj(self.bot)
                                    function_results.append(f"执行函数 {name}(bot): {r}")
                                else:
                                    # 尝试无参调用
                                    try:
                                        r = obj()
                                        function_results.append(f"执行函数 {name}(): {r}")
                                    except TypeError:
                                        function_results.append(f"跳过函数 {name}（需要参数但无法自动提供）")
                        except Exception as e:
                            err_line = f"执行函数 {name} 时出错: {str(e)}"
                            function_results.append(err_line)
                            function_error_lines.append(err_line)
                            # 收集完整的 traceback
                            tb = traceback.format_exc()
                            function_error_lines.append(f"函数 {name} 的完整错误堆栈:\n{tb}")

            output = stdout_capture.getvalue()
            error_output = stderr_capture.getvalue()
            if function_results:
                output += ("\n" if output else "") + "\n".join(function_results)

            if error_output:
                return {
                    "success": False,
                    "output": output,
                    "error": error_output,
                    "result": None,
                    "traceback": ""
                }

            # 如果函数级别出现错误，即使没有stderr，也应视为失败
            if function_error_lines:
                # 提取 traceback 信息
                traceback_info = ""
                error_info = []
                for line in function_error_lines:
                    if "完整错误堆栈:" in line:
                        traceback_info += line + "\n"
                    else:
                        error_info.append(line)
                
                return {
                    "success": False,
                    "output": output,
                    "error": "\n".join(error_info),
                    "result": None,
                    "traceback": traceback_info.strip()
                }

            return {
                "success": True,
                "output": output,
                "error": "",
                "result": None,
                "traceback": ""
            }

        except Exception as e:
            tb = traceback.format_exc()
            return {
                "success": False,
                "output": stdout_capture.getvalue(),
                "error": str(e),
                "result": None,
                "traceback": tb
            }


# 创建全局代码运行器实例
code_runner = CodeRunner()