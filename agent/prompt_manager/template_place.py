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