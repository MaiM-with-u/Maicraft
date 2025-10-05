"""
主模式 - 默认的主动决策模式
允许LLM参与决策，处理正常的AI行为
"""

from agent.modes.base import DecisionMode, ModeType
from utils.logger import get_logger

logger = get_logger("MainMode")


class MainMode(DecisionMode):
    """主模式 - 默认的主动决策模式"""

    def __init__(self):
        super().__init__()

        # 基本配置
        self.name = "主模式"
        self.description = "默认的主动决策模式，允许LLM参与所有决策"
        self.priority = 0  # 最低优先级
        self.max_duration = None  # 永不超时
        self.auto_restore = False  # 不自动恢复

    @property
    def mode_type(self) -> str:
        """返回模式类型"""
        return ModeType.MAIN.value

    def register_to_system(self):
        """注册模式到模式系统"""
        try:
            from agent.mai_mode import mode_manager

            # 注册模式实例
            mode_manager.register_mode(self)

            logger.debug("主模式已注册到模式系统")

        except Exception as e:
            logger.error(f"模式注册失败: {e}")

    async def activate(self, reason: str, triggered_by: str) -> None:
        """激活主模式"""
        logger.info(f"🟢 激活主模式: {reason}")

    async def deactivate(self, reason: str, triggered_by: str) -> None:
        """停用主模式"""
        logger.info(f"🟡 停用主模式: {reason}")


# 全局主模式实例
main_mode = MainMode()


def get_main_mode():
    """获取主模式实例"""
    return main_mode


def register_main_mode():
    """注册主模式到模式系统"""
    main_mode.register_to_system()
