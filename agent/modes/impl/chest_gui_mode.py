"""
箱子GUI主动决策模式 - 处理箱子操作任务
由LLM决策触发，执行箱子物品存取任务
"""

from agent.modes.base import DecisionMode, ModeType
from utils.logger import get_logger

logger = get_logger("ChestGUIMode")


class ChestGUIMode(DecisionMode):
    """箱子GUI主动决策模式 - 执行箱子操作任务"""

    def __init__(self, position=None):
        super().__init__()

        # 基本配置
        self.name = "箱子操作模式"
        self.description = "执行箱子物品存取任务的主动决策模式"
        self.priority = 50  # 中等优先级
        self.max_duration = 300  # 5分钟超时
        self.auto_restore = True
        self.restore_delay = 5

        # 任务相关配置
        self.position = position
        self.chest_gui = None

    @property
    def mode_type(self) -> str:
        """返回模式类型"""
        return ModeType.CHEST_GUI.value

    async def activate(self, reason: str, triggered_by: str) -> None:
        """激活箱子GUI模式"""
        logger.info(f"📦 激活箱子GUI模式: {reason}")

        # 如果有位置信息，初始化GUI
        if self.position:
            try:
                from agent.sim_gui.chest import ChestSimGui
                self.chest_gui = ChestSimGui(self.position, None)  # llm_client 稍后设置
                logger.debug(f"初始化箱子GUI: {self.position}")
            except Exception as e:
                logger.error(f"初始化箱子GUI失败: {e}")

    async def deactivate(self, reason: str, triggered_by: str) -> None:
        """停用箱子GUI模式"""
        logger.info(f"🟡 停用箱子GUI模式: {reason}")

        # 清理GUI资源
        if self.chest_gui:
            self.chest_gui = None

    def update_position(self, position):
        """更新箱子位置"""
        self.position = position
        self.description = f"执行箱子物品存取任务 - 位置: {position.x},{position.y},{position.z}" if position else "执行箱子物品存取任务的主动决策模式"


# 全局箱子GUI模式实例
chest_gui_mode = ChestGUIMode()
