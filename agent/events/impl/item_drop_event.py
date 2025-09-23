"""
物品丢弃事件实现
"""

from typing import Optional, Dict, Any, List
from typing_extensions import TypedDict
from ..base_event import BaseEvent
from ..event_types import EventType
from ...common.basic_class import Position


class DroppedItem(TypedDict):
    """丢弃的物品信息"""

    id: int
    name: str
    displayName: str
    count: int
    metadata: Optional[Dict[str, Any]]


class ItemDropEventData(TypedDict):
    dropped: List[DroppedItem]
    position: Position


class ItemDropEvent(BaseEvent[ItemDropEventData]):
    """物品丢弃事件"""

    EVENT_TYPE = EventType.ITEM_DROP.value

    def __init__(
        self, type: str, gameTick: int, timestamp: float, data: ItemDropEventData = None
    ):
        """初始化物品丢弃事件"""
        super().__init__(type, gameTick, timestamp, data)

    def get_description(self) -> str:
        """获取事件的描述信息"""
        dropped_items = self.data.dropped

        items_str = self._build_items_description(dropped_items)
        position = self.get_drop_position()

        if position:
            return f"物品 {items_str} 掉落在位置 {position}"
        else:
            return f"物品 {items_str} 掉落"

    def _build_items_description(self, dropped_items: List[DroppedItem]) -> str:
        """构建物品描述字符串的辅助方法"""
        if not dropped_items:
            return "物品"

        # 构建物品描述
        item_descriptions = []
        for item in dropped_items:
            display_name = item.get("displayName", item.get("name", "未知物品"))
            count = item.get("count", 1)
            count_str = f" x{count}" if count > 1 else ""
            item_descriptions.append(f"{display_name}{count_str}")

        return ", ".join(item_descriptions)

    def to_dict(self) -> dict:
        """转换为字典格式"""
        result = super().to_dict()
        result.update(
            {
                "dropped": self.data.dropped,
                "position": self.data.position,
            }
        )
        return result

    def get_drop_position(self) -> Optional[Position]:
        """获取物品丢弃的位置"""
        return self.data.position

    def get_dropped_items(self) -> List[DroppedItem]:
        """获取丢弃的物品列表"""
        return self.data.dropped

    def get_total_item_count(self) -> int:
        """获取丢弃的物品总数"""
        return sum(item.get("count", 0) for item in self.data.dropped)

    def get_unique_item_names(self) -> List[str]:
        """获取丢弃的唯一物品名称列表"""
        return [item.get("name", "unknown") for item in self.data.dropped]

    def get_item_names_string(self) -> str:
        """获取物品名称字符串，用于日志记录"""
        return ", ".join(self.get_unique_item_names())

    def get_item_counts_string(self) -> str:
        """获取物品数量字符串，用于日志记录"""
        counts = [str(item.get("count", 0)) for item in self.data.dropped]
        return ", ".join(counts)
