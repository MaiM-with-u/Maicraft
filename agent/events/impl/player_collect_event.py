"""
玩家收集事件实现
"""
from typing import Optional, Dict, Any
from typing_extensions import TypedDict
from ..base_event import BaseEvent
from ..event_types import EventType
from ...common.basic_class import Entity


class CollectedItem(TypedDict):
    """收集的物品信息"""
    id: int
    name: str
    displayName: str
    count: int
    metadata: Optional[Dict[str, Any]]


class PlayerCollectEventData(TypedDict):
    collector: Entity
    collected: list[CollectedItem]


class PlayerCollectEvent(BaseEvent[PlayerCollectEventData]):
    """玩家收集事件"""

    EVENT_TYPE = EventType.PLAYER_COLLECT.value

    def __init__(self, type: str, gameTick: int, timestamp: float, data: PlayerCollectEventData = None):
        """初始化玩家收集事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        """获取事件的描述信息"""
        username = self.get_collector_username()
        collected_items = self.data.collected

        items_str = self._build_items_description(collected_items)
        return f"{username}收集了 {items_str}"

    def to_context_string(self) -> str:
        """转换为上下文字符串，用于AI理解"""
        username = self.get_collector_username()
        collected_items = self.data.collected

        items_str = self._build_items_description(collected_items)
        return f"[playerCollect] {username} 收集了 {items_str}"

    def _build_items_description(self, collected_items: list[CollectedItem]) -> str:
        """构建物品描述字符串的辅助方法"""
        if not collected_items:
            return "物品"

        # 构建物品描述
        item_descriptions = []
        for item in collected_items:
            display_name = item.get('displayName', item.get('name', '未知物品'))
            count = item.get('count', 1)
            count_str = f" x{count}" if count > 1 else ""
            item_descriptions.append(f"{display_name}{count_str}")

        return ", ".join(item_descriptions)

    def to_dict(self) -> dict:
        """转换为字典格式"""
        result = super().to_dict()
        result["player_name"] = self.get_collector_username()
        result.update({
            "collector": self.data.collector,
            "collected": self.data.collected,
        })
        return result

    def get_collector_username(self) -> str:
        """获取收集者的用户名"""
        # Entity对象使用属性访问而不是字典访问
        username = getattr(self.data.collector, 'username', None)
        if username:
            return username

        # 如果没有username，尝试使用name
        name = getattr(self.data.collector, 'name', None)
        return name or '未知玩家'

    def get_collector_position(self) -> Optional[Dict[str, float]]:
        """获取收集者的位置"""
        position = getattr(self.data.collector, 'position', None)
        if position is None:
            return None

        # 如果position是Position对象，转换为字典
        if hasattr(position, 'x') and hasattr(position, 'y') and hasattr(position, 'z'):
            return {
                'x': position.x,
                'y': position.y,
                'z': position.z
            }

        # 如果已经是字典格式，直接返回，否则返回None
        return position if isinstance(position, dict) else None

    def get_collected_items(self) -> list[CollectedItem]:
        """获取收集的物品列表"""
        return self.data.collected

    def get_total_item_count(self) -> int:
        """获取收集的物品总数"""
        return sum(item.get('count', 0) for item in self.data.collected)

    def get_unique_item_names(self) -> list[str]:
        """获取收集的唯一物品名称列表"""
        return [item.get('name', 'unknown') for item in self.data.collected]

    def is_self_collect(self, bot_entity_id: int = None) -> bool:
        """判断是否是机器人自己收集的物品"""
        if bot_entity_id is None:
            return False

        collector_id = getattr(self.data.collector, 'id', None)
        return collector_id == bot_entity_id
