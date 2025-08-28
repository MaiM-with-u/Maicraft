from agent.prompt_manager.prompt_manager import PromptTemplate, prompt_manager

def init_templates_place() -> None:
    """初始化提示词模板"""
    prompt_manager.register_template(
    PromptTemplate(
    name="minecraft_place_block",
    template="""
你的用户名是Mai，是一个Minecraft玩家。你现在想要放置一个{block_type}方块在某个坐标

你的位置: 
{player_position}

你附近的方块信息：
{nearby_block_info}

建议：
{suggest_position}

请根据建议和附近方块信息，用json输出一个放置{block_type}的坐标，要求：
1. 该坐标不能有方块
2. 你可以在air处放置方块
3. 你不能放置方块到你{self_area}

{{
"x":坐标x,
"y":坐标y,
"z":坐标z,
"reason":"选择这个位置的理由"
}}

用json格式输出坐标，请你只输出json，不要输出其他内容
""",
    description="Minecraft放置方块模板",
    parameters=["block_type", "player_position", "nearby_block_info", "suggest_position","self_area"],
    ))  
    
    
    prompt_manager.register_template(
    PromptTemplate(
    name="minecraft_position",
    template="""
你的用户名是Mai，是一个Minecraft玩家。

你的位置: 
{player_position}

你附近的方块信息：
{nearby_block_info}

请根据建议和附近方块信息，用坐标列表输出能够站立和前往的位置列表
非常重要：这些坐标要求：
1. 位置要求：有两格高空间容纳玩家，即坐标的上方一格为空气，坐标本身为空气
2. 脚下方块要求：脚下方块不为空气，能够站立
3. 如果有多个坐标位置较近，可以合并成一个


{
    "stand_positions": [
        {
            "x": 坐标x,
            "y": 坐标y,
            "z": 坐标z,
            "description": "这个位置的简要描述"
        },
        {
            "x": 坐标x,
            "y": 坐标y,
            "z": 坐标z,
            "description": "这个位置的简要描述"
        }
        // 可以有更多坐标组
    ]
}

请只输出位置列表，不要输出其他内容：
""",
    description="Minecraft放置方块模板",
    parameters=["player_position", "nearby_block_info"],
    ))  
