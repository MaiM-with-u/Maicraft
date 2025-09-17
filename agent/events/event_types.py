"""
事件类型常量定义
面向对象设计：事件分类由各事件类的get_category()方法提供
"""

# 实际存在的事件类型常量（用于类型检查和配置）
CHAT_EVENT = "chat"
PLAYER_JOINED_EVENT = "playerJoined"
PLAYER_LEFT_EVENT = "playerLeft"
DEATH_EVENT = "death"
SPAWN_EVENT = "spawn"
RAIN_EVENT = "rain"
KICKED_EVENT = "kicked"
SPAWN_RESET_EVENT = "spawnReset"
HEALTH_EVENT = "health"
ENTITY_HURT_EVENT = "entityHurt"
ENTITY_DEAD_EVENT = "entityDead"
PLAYER_COLLECT_EVENT = "playerCollect"

# 所有支持的事件类型
SUPPORTED_EVENTS = {
    CHAT_EVENT,
    PLAYER_JOINED_EVENT,
    PLAYER_LEFT_EVENT,
    DEATH_EVENT,
    SPAWN_EVENT,
    RAIN_EVENT,
    KICKED_EVENT,
    SPAWN_RESET_EVENT,
    HEALTH_EVENT,
    ENTITY_HURT_EVENT,
    ENTITY_DEAD_EVENT,
    PLAYER_COLLECT_EVENT,
}
