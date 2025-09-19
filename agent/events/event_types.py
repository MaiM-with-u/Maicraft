"""
事件类型枚举定义
面向对象设计：事件分类由各事件类的get_category()方法提供
"""

from enum import Enum


class EventType(Enum):
    """事件类型枚举"""

    CHAT = "chat"
    PLAYER_JOINED = "playerJoined"
    PLAYER_LEFT = "playerLeft"
    DEATH = "death"
    SPAWN = "spawn"
    RAIN = "rain"
    KICKED = "kicked"
    SPAWN_RESET = "spawnReset"
    HEALTH = "health"
    ENTITY_HURT = "entityHurt"
    ENTITY_DEAD = "entityDead"
    PLAYER_COLLECT = "playerCollect"
    ITEM_DROP = "itemDrop"
    BREATH = "breath"


# 所有支持的事件类型
SUPPORTED_EVENTS = {event_type.value for event_type in EventType}
