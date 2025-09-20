"""
伤害响应处理器包

专门处理Minecraft中的实体受伤事件，根据伤害来源采取不同的响应策略：
- 玩家攻击：通过LLM进行交涉对话
- 敌对生物攻击：直接反击
- 生命濒危时：请求附近玩家帮助
"""

from .hurt_response_handler import setup_hurt_response_handlers

__all__ = ["setup_hurt_response_handlers"]
