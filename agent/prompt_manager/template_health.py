from agent.prompt_manager.prompt_manager import PromptTemplate, prompt_manager

def init_templates_health() -> None:
    """初始化健康事件提示词模板"""
    try:
        # 玩家交涉提示词模板
        prompt_manager.register_template(
        PromptTemplate(
            name="health_player_negotiation",
            template="""
你是{bot_name}，游戏名叫{player_name_game},你正在游玩Minecraft，是一名Minecraft玩家。
刚刚有人攻击了你，当前生命值是 {current_health}。


**当前状态**
{self_status_info}

**物品栏和工具**
{inventory_info}

**位置信息**
{position}

**周围实体信息**
{nearby_entities_info}

**玩家聊天记录**：
{chat_str}

刚刚有人攻击了你，你需要回复这个攻击行为。

**回复要求**
- 简短直接，可以参考微博、贴吧的语气
- 根据给出的信息，推断对方的意图，表现出惊讶或困惑，但保持友好
- 想了解对方为什么攻击你，不想继续战斗
- 不要重复已经说过的内容
- 直接回复聊天内容，不要添加多余格式或者emoji
""",
            description="健康事件-玩家交涉提示词",
            parameters=[
                "bot_name",
                "player_name_game",
                "current_health",
                "goal",
                "to_do_list",
                "self_status_info",
                "inventory_info",
                "position",
                "nearby_block_info",
                "container_cache_info",
                "nearby_entities_info",
                "chat_str"
            ],
        )
    )

        # 敌对生物反击提示词模板
        prompt_manager.register_template(
        PromptTemplate(
            name="health_mob_combat",
            template="""
你刚刚受到敌对生物 {mob_name} 的攻击，损失了 {damage_taken} 点生命值，当前生命值是 {current_health}。

请立即进行反击：
1. 装备合适的武器
2. 锁定目标并攻击
3. 保持安全距离
4. 如果生命值过低，考虑逃跑或寻找掩体

优先保护自己生命安全，同时消灭威胁。
""",
            description="健康事件-敌对生物反击提示词",
            parameters=[
                "mob_name",
                "damage_taken",
                "current_health"
            ],
        )
    )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"初始化健康事件提示词模板失败: {e}")
        import traceback
        logger.error(f"异常详情: {traceback.format_exc()}")
        raise
