"""
熔炉GUI主动决策模式 - 处理熔炉操作任务
由LLM决策触发，执行熔炉冶炼任务
"""

from agent.modes.base import DecisionMode, ModeType
from utils.logger import get_logger

logger = get_logger("FurnaceGUIMode")


class FurnaceGUIMode(DecisionMode):
    """熔炉GUI主动决策模式 - 执行熔炉操作任务"""

    def __init__(self, position=None):
        super().__init__()

        # 基本配置
        self.name = "熔炉操作模式"
        self.description = "执行熔炉冶炼任务的主动决策模式"
        self.priority = 50  # 中等优先级
        self.max_duration = 300  # 5分钟超时
        self.auto_restore = True
        self.restore_delay = 5

        # 任务相关配置
        self.position = position
        self.furnace_gui = None

    @property
    def mode_type(self) -> str:
        """返回模式类型"""
        return ModeType.FURNACE_GUI.value

    async def activate(self, reason: str, triggered_by: str) -> None:
        """激活熔炉GUI模式"""
        logger.info(f"🔥 激活熔炉GUI模式: {reason}")

        # GUI初始化将在MaiAgent中完成，这里只记录状态
        logger.debug(f"熔炉GUI模式激活，等待GUI操作")

    async def deactivate(self, reason: str, triggered_by: str) -> None:
        """停用熔炉GUI模式"""
        logger.info(f"🟡 停用熔炉GUI模式: {reason}")

        # 清理GUI资源
        if self.furnace_gui:
            self.furnace_gui = None

    def update_position(self, position):
        """更新熔炉位置"""
        self.position = position
        self.description = f"执行熔炉操作任务 - 位置: {position.x},{position.y},{position.z}" if position else "执行熔炉冶炼任务的主动决策模式"


# 全局熔炉GUI模式实例
furnace_gui_mode = FurnaceGUIMode()
