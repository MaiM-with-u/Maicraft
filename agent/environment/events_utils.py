from agent.environment.basic_info import Event
from config import global_config

def get_event_description(event: Event) -> str:
    """获取事件描述"""
    
    # logger.info(f"事件: {event}")
    
    # 获取玩家名称，优先使用事件中的玩家名称
    player_name = event.player_name or "未知玩家"
    if player_name == global_config.bot.player_name:
        base_desc = f"你({player_name})"
    else:
        base_desc = f"玩家{player_name}"
    
    
    # 根据事件类型生成详细描述
    # if event.type == "playerMove" and event.old_position and event.new_position:
    #     old_pos = event.old_position
    #     new_pos = event.new_position
    #     return f"{base_desc} 从 ({old_pos.x:.1f}, {old_pos.y:.1f}, {old_pos.z:.1f}) 移动到 ({new_pos.x:.1f}, {new_pos.y:.1f}, {new_pos.z:.1f})"
    
    # elif event.type == "blockBreak" and event.block:
    #     block = event.block
    #     pos = block.position
    #     return f"{base_desc} 破坏了 {block.name} 在 ({pos.x:.1f}, {pos.y:.1f}, {pos.z:.1f})"
    
    # elif event.type == "blockPlace" and event.block:
    #     block = event.block
    #     pos = block.position
    #     return f"{base_desc} 放置了 {block.name} 在 ({pos.x:.1f}, {pos.y:.1f}, {pos.z:.1f})"
    
    # elif event.type == "experienceUpdate":
    #     return f"{base_desc} 经验值更新: {event.experience}, 等级: {event.level}"
    
    # elif event.type == "healthUpdate":
    #     health_info = f"生命值: {event.health}"
    #     food_info = f"饥饿值: {event.food}"
    #     saturation_info = f"饱和度: {event.saturation}" if event.saturation is not None else ""
        
    #     info_parts = [health_info, food_info]
    #     if saturation_info:
    #         info_parts.append(saturation_info)
        
        # return f"{base_desc} 状态更新: {', '.join(info_parts)}"
    
    if event.type == "playerJoin":
        return f"{base_desc} 加入了游戏"
    
    elif event.type == "playerLeave":
        return f"{base_desc} 离开了游戏"
    
    elif event.type == "playerDeath":
        return f"{base_desc} 死亡了"
    
    elif event.type == "playerRespawn":
        if event.new_position:
            pos = event.new_position
            return f"{base_desc} 重生于 ({pos.x:.1f}, {pos.y:.1f}, {pos.z:.1f})"
        else:
            return f"{base_desc} 重生了"
    
    elif event.type == "playerKick":
        if hasattr(event, 'kick_reason') and event.kick_reason:
            return f"{base_desc} 被踢出游戏: {event.kick_reason}"
        else:
            return f"{base_desc} 被踢出游戏"
    
    elif event.type == "entityHurt":
        if hasattr(event, 'entity_name') and event.entity_name:
            entity_name = event.entity_name
            if hasattr(event, 'damage') and event.damage is not None:
                return f"{base_desc} 对 {entity_name} 造成了 {event.damage} 点伤害"
            else:
                return f"{base_desc} 攻击了 {entity_name}"
        else:
            return f"{base_desc} 攻击了实体"
    
    elif event.type == "entityDeath":
        if hasattr(event, 'entity_name') and event.entity_name:
            entity_name = event.entity_name
            if hasattr(event, 'entity_position') and event.entity_position:
                pos = event.entity_position
                return f"{base_desc} 击杀了 {entity_name} 在 ({pos.x:.1f}, {pos.y:.1f}, {pos.z:.1f})"
            else:
                return f"{base_desc} 击杀了 {entity_name}"
        else:
            return f"{base_desc} 击杀了实体"
    
    elif event.type == "weatherChange":
        if hasattr(event, 'weather') and event.weather:
            return f"{base_desc} 天气变为: {event.weather}"
        else:
            return f"{base_desc} 天气发生了变化"
    
    elif event.type == "spawnPointReset":
        return f"{base_desc} 重置了出生点"
    
    else:
        return ""