"""
Token使用量管理器
负责跟踪和管理LLM API调用的token使用情况

全局管理器使用方式：
1. 直接创建 TokenUsageManager() - 会自动使用全局实例
2. 使用 get_global_token_manager() - 显式获取全局实例
3. 使用 set_global_token_manager_callback() - 设置回调函数（用于WebSocket推送）

注意：所有地方都应该使用全局实例以确保数据一致性
"""

import json
import time
from typing import Dict, Any, Optional, Callable
from pathlib import Path
import tomllib
from utils.logger import get_logger

# 全局Token使用量管理器实例
global_token_manager = None

def get_global_token_manager() -> "TokenUsageManager":
    """获取全局Token使用量管理器实例

    这是获取全局Token使用量管理器的推荐方式。
    确保所有地方都使用同一个实例以保持数据一致性。
    """
    global global_token_manager
    if global_token_manager is None:
        # 如果还没有全局实例，创建一个，但不设置回调（回调应该通过set_global_token_manager_callback设置）
        global_token_manager = TokenUsageManager(use_global=False)
    return global_token_manager

def set_global_token_manager_callback(callback: Optional[Callable[[str, Dict[str, Any]], None]]) -> None:
    """设置全局Token使用量管理器的回调"""
    global global_token_manager
    if global_token_manager is None:
        global_token_manager = TokenUsageManager(update_callback=callback)
    else:
        global_token_manager.update_callback = callback

class TokenUsageManager:
    """Token使用量管理器"""

    def __init__(self, usage_dir: str = "usage", update_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None, use_global: bool = True):
        """初始化token使用量管理器

        Args:
            usage_dir: 使用量记录文件存储目录，相对于项目根目录
            update_callback: 使用量更新时的回调函数，参数为(model_name, usage_data)
            use_global: 是否使用全局实例
        """
        # 如果使用全局实例且已存在，则返回现有实例
        global global_token_manager
        if use_global and global_token_manager is not None:
            # 如果提供了新回调，更新现有实例的回调
            if update_callback:
                global_token_manager.update_callback = update_callback
            # 复制现有实例的所有属性到self
            self.__dict__.update(global_token_manager.__dict__)
            return

        # 获取项目根目录
        project_root = Path(__file__).parent.parent
        self.usage_dir = project_root / usage_dir
        self.usage_dir.mkdir(exist_ok=True)

        # 初始化logger
        self.logger = get_logger("TokenUsageManager")

        # 加载模型价格配置
        self.model_prices = self._load_model_prices()

        # 设置更新回调
        self.update_callback = update_callback

        # 如果使用全局实例，保存到全局变量
        if use_global:
            global_token_manager = self
        
    def _load_model_prices(self) -> Dict[str, Dict[str, float]]:
        """加载模型价格配置
        
        Returns:
            模型价格配置字典
        """
        price_file = Path(__file__).parent / "model_price.toml"
        
        if not price_file.exists():
            self._get_logger().info("模型价格配置文件不存在，将无法计算费用")
            return {}
        
        try:
            with open(price_file, 'rb') as f:
                prices = tomllib.load(f)
                self._get_logger().info(f"成功加载模型价格配置: {list(prices.keys())}")
                return prices
        except Exception as e:
            self._get_logger().warning(f"读取模型价格配置失败: {e}")
            return {}
    
    def _get_model_price(self, model_name: str) -> Optional[Dict[str, float]]:
        """获取指定模型的价格配置
        
        Args:
            model_name: 模型名称
            
        Returns:
            价格配置字典，如果不存在则返回None
        """
        # 尝试精确匹配
        if model_name in self.model_prices:
            return self.model_prices[model_name]
        
        # 尝试模糊匹配（移除版本号等后缀）
        for price_model in self.model_prices.keys():
            if model_name.startswith(price_model.split('-')[0]) or price_model in model_name:
                return self.model_prices[price_model]
        
        return None
    
    def _calculate_cost(self, model_name: str, prompt_tokens: int, completion_tokens: int) -> Dict[str, Any]:
        """计算token使用费用
        
        Args:
            model_name: 模型名称
            prompt_tokens: 输入token数量
            completion_tokens: 输出token数量
            
        Returns:
            费用计算信息字典
        """
        price_config = self._get_model_price(model_name)
        
        if not price_config:
            return {
                "has_price": False,
                "cost": 0.0,
                "cost_usd": 0.0,
                "price_in": 0.0,
                "price_out": 0.0,
                "message": f"模型 {model_name} 未找到价格配置"
            }
        
        # 价格单位：每1000000个token的价格（通常是美元）
        price_in = price_config.get("price_in", 0.0)
        price_out = price_config.get("price_out", 0.0)
        
        # 计算费用（转换为每token的价格）
        cost_in = (prompt_tokens / 1000000.0) * price_in
        cost_out = (completion_tokens / 1000000.0) * price_out
        total_cost = cost_in + cost_out
        
        return {
            "has_price": True,
            "cost": total_cost,
            "cost_usd": total_cost,  # 假设价格单位为美元
            "price_in": price_in,
            "price_out": price_out,
            "cost_in": cost_in,
            "cost_out": cost_out,
            "message": "费用计算成功"
        }
    
    def _get_logger(self):
        """获取logger实例"""
        return self.logger
    
    def _get_usage_file_path(self, model_name: str) -> Path:
        """获取指定模型的使用量文件路径
        
        Args:
            model_name: 模型名称
            
        Returns:
            使用量文件路径
        """
        # 清理模型名称，移除特殊字符
        safe_model_name = "".join(c for c in model_name if c.isalnum() or c in ('-', '_', '.'))
        return self.usage_dir / f"{safe_model_name}_usage.json"
    
    def _load_current_usage(self, model_name: str) -> Dict[str, Any]:
        """加载当前模型的使用量数据
        
        Args:
            model_name: 模型名称
            
        Returns:
            当前使用量数据字典
        """
        file_path = self._get_usage_file_path(model_name)
        
        if not file_path.exists():
            # 如果文件不存在，返回初始数据
            return {
                "model_name": model_name,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_tokens": 0,
                "total_calls": 0,
                "total_cost": 0.0,
                "first_call_time": None,
                "last_call_time": None,
                "last_updated": None
            }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 确保所有必需字段都存在
                default_data = {
                    "model_name": model_name,
                    "total_prompt_tokens": 0,
                    "total_completion_tokens": 0,
                    "total_tokens": 0,
                    "total_calls": 0,
                    "total_cost": 0.0,
                    "first_call_time": None,
                    "last_call_time": None,
                    "last_updated": None
                }
                default_data.update(data)

                # 向后兼容：将旧格式的浮点时间戳转换为整数毫秒时间戳
                for field in ["first_call_time", "last_call_time", "last_updated"]:
                    if default_data[field] is not None and isinstance(default_data[field], float):
                        # 如果是浮点数且小于1e10，说明是秒时间戳，需要转换为毫秒
                        if default_data[field] < 1e10:
                            default_data[field] = int(default_data[field] * 1000)
                        else:
                            # 如果已经大于1e10，说明已经是毫秒时间戳
                            default_data[field] = int(default_data[field])

                return default_data
        except (json.JSONDecodeError, IOError) as e:
            self._get_logger().warning(f"读取使用量文件失败: {e}，使用默认值")
            return {
                "model_name": model_name,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_tokens": 0,
                "total_calls": 0,
                "total_cost": 0.0,
                "first_call_time": None,
                "last_call_time": None,
                "last_updated": None
            }
    
    def _save_usage(self, model_name: str, usage_data: Dict[str, Any]):
        """保存使用量数据到文件
        
        Args:
            model_name: 模型名称
            usage_data: 使用量数据
        """
        file_path = self._get_usage_file_path(model_name)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(usage_data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            self._get_logger().error(f"保存使用量文件失败: {e}")
    
    def record_usage(self, model_name: str, prompt_tokens: int, completion_tokens: int, total_tokens: int):
        """记录一次token使用量

        Args:
            model_name: 模型名称
            prompt_tokens: 输入token数量
            completion_tokens: 输出token数量
            total_tokens: 总token数量
        """
        current_time = int(time.time() * 1000)  # 转换为整数毫秒时间戳
        current_usage = self._load_current_usage(model_name)

        # 计算本次调用的费用
        cost_info = self._calculate_cost(model_name, prompt_tokens, completion_tokens)

        # 累加token使用量
        current_usage["total_prompt_tokens"] += prompt_tokens
        current_usage["total_completion_tokens"] += completion_tokens
        current_usage["total_tokens"] += total_tokens
        current_usage["total_calls"] += 1

        # 累加费用
        current_usage["total_cost"] += cost_info["cost"]

        # 更新时间戳
        if current_usage["first_call_time"] is None:
            current_usage["first_call_time"] = current_time
        current_usage["last_call_time"] = current_time
        current_usage["last_updated"] = current_time
        
        # 保存到文件
        self._save_usage(model_name, current_usage)

        # 触发更新回调（用于WebSocket推送）
        if self.update_callback:
            try:
                self.update_callback(model_name, current_usage)
            except Exception as e:
                self._get_logger().warning(f"执行更新回调失败: {e}")

        # 记录日志
        cost_msg = f"，费用: {cost_info['cost']:.6f}" if cost_info["has_price"] else "，无价格配置"
        self._get_logger().info(
            f"模型: {model_name},[{prompt_tokens}+{completion_tokens}][{cost_msg}]"
        )
    
    def get_usage_summary(self, model_name: str) -> Dict[str, Any]:
        """获取指定模型的使用量摘要
        
        Args:
            model_name: 模型名称
            
        Returns:
            使用量摘要字典
        """
        return self._load_current_usage(model_name)
    
    def get_all_models_usage(self) -> Dict[str, Dict[str, Any]]:
        """获取所有模型的使用量摘要
        
        Returns:
            所有模型使用量摘要字典
        """
        all_usage = {}
        
        if not self.usage_dir.exists():
            return all_usage
        
        for file_path in self.usage_dir.glob("*_usage.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    model_name = data.get("model_name", file_path.stem.replace("_usage", ""))

                    # 向后兼容：将旧格式的浮点时间戳转换为整数毫秒时间戳
                    for field in ["first_call_time", "last_call_time", "last_updated"]:
                        if data.get(field) is not None and isinstance(data[field], float):
                            # 如果是浮点数且小于1e10，说明是秒时间戳，需要转换为毫秒
                            if data[field] < 1e10:
                                data[field] = int(data[field] * 1000)
                            else:
                                # 如果已经大于1e10，说明已经是毫秒时间戳
                                data[field] = int(data[field])

                    all_usage[model_name] = data
            except (json.JSONDecodeError, IOError) as e:
                self._get_logger().warning(f"读取使用量文件失败 {file_path}: {e}")
        
        return all_usage
    
    def get_total_cost_summary(self) -> Dict[str, Any]:
        """获取所有模型的总费用摘要
        
        Returns:
            总费用摘要字典
        """
        all_usage = self.get_all_models_usage()
        
        total_cost = 0.0
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_calls = 0
        
        for model_data in all_usage.values():
            total_cost += model_data.get("total_cost", 0.0)
            total_prompt_tokens += model_data.get("total_prompt_tokens", 0)
            total_completion_tokens += model_data.get("total_completion_tokens", 0)
            total_calls += model_data.get("total_calls", 0)
        
        return {
            "total_cost": total_cost,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_tokens": total_prompt_tokens + total_completion_tokens,
            "total_calls": total_calls,
            "model_count": len(all_usage)
        }
    
    def format_usage_summary(self, model_name: str) -> str:
        """格式化使用量摘要为可读字符串
        
        Args:
            model_name: 模型名称
            
        Returns:
            格式化的使用量摘要字符串
        """
        usage = self.get_usage_summary(model_name)
        
        if usage["total_calls"] == 0:
            return f"模型 {model_name} 暂无使用记录"
        
        first_call = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(usage["first_call_time"])) if usage["first_call_time"] else "未知"
        last_call = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(usage["last_call_time"])) if usage["last_call_time"] else "未知"
        
        # 获取价格信息
        price_config = self._get_model_price(model_name)
        price_info = ""
        if price_config:
            price_info = f"\n价格配置: 输入{price_config['price_in']}/1K tokens, 输出{price_config['price_out']}/1K tokens"
        
        summary = f"""
模型: {model_name}
总调用次数: {usage['total_calls']}
总输入Token: {usage['total_prompt_tokens']:,}
总输出Token: {usage['total_completion_tokens']:,}
总Token: {usage['total_tokens']:,}
总费用: {usage['total_cost']:.6f}
首次调用: {first_call}
最后调用: {last_call}{price_info}
        """.strip()
        
        return summary
    
    def format_total_cost_summary(self) -> str:
        """格式化总费用摘要为可读字符串
        
        Returns:
            格式化的总费用摘要字符串
        """
        cost_summary = self.get_total_cost_summary()
        
        if cost_summary["total_calls"] == 0:
            return "暂无任何模型的使用记录"
        
        summary = f"""
=== 所有模型费用汇总 ===
总调用次数: {cost_summary['total_calls']}
使用模型数: {cost_summary['model_count']}
总输入Token: {cost_summary['total_prompt_tokens']:,}
总输出Token: {cost_summary['total_completion_tokens']:,}
总Token: {cost_summary['total_tokens']:,}
总费用: {cost_summary['total_cost']:.6f}
        """.strip()
        
        return summary
