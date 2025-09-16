"""
事件类型常量定义
面向对象设计：事件分类由各事件类的get_category()方法提供
"""

# 事件类型常量（用于类型检查和配置）
CHAT_EVENT = "chat"
PLAYER_JOIN_EVENT = "playerJoin"
PLAYER_LEAVE_EVENT = "playerLeave"
PLAYER_MOVE_EVENT = "playerMove"
BLOCK_BREAK_EVENT = "blockBreak"
BLOCK_PLACE_EVENT = "blockPlace"
ITEM_PICKUP_EVENT = "itemPickup"
ITEM_DROP_EVENT = "itemDrop"
ENTITY_DAMAGE_EVENT = "entity_damage"
ENTITY_DEATH_EVENT = "entity_death"
HEALTH_UPDATE_EVENT = "healthUpdate"

# 事件分类常量
CHAT_CATEGORY = "chat"
PLAYER_CATEGORY = "player"
BLOCK_CATEGORY = "block"
ITEM_CATEGORY = "item"
ENTITY_CATEGORY = "entity"
UNKNOWN_CATEGORY = "unknown"

# 所有事件分类
ALL_CATEGORIES = {CHAT_CATEGORY, PLAYER_CATEGORY, BLOCK_CATEGORY, ITEM_CATEGORY, ENTITY_CATEGORY}
