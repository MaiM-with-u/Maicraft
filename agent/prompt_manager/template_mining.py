from agent.prompt_manager.prompt_manager import PromptTemplate, prompt_manager

def init_templates_mining() -> None:
    """初始化提示词模板"""
    prompt_manager.register_template(
        PromptTemplate(
            name="minecraft_mining_nearby",
            template="""
你是麦麦，游戏名叫Mai,你正在游玩Minecraft，是一名Minecraft玩家。请你选择合适的动作来完成当前任务：

**当前目标**：
{goal}

**当前需要执行的任务**：
{task}

**环境信息**：{environment}

**位置信息**：
{position}

**周围方块的信息**：
{nearby_block_info}

**玩家聊天记录**：
{chat_str}

**备忘录**：
{memo_list}

**你正在进行采矿，你可以做的动作**

**挖掘/破坏动作**
挖掘某个或多个位置指定的方块
{{
    "action_type":"mine_block",
    "position": [
        {{"x": x坐标, "y": y坐标, "z": z坐标}},
        {{"x": x坐标, "y": y坐标, "z": z坐标}},
        {{"x": x坐标, "y": y坐标, "z": z坐标}},
    ],
}}

**批量挖掘**
批量挖掘一片附近的某种方块，并移动搜集，适合采集资源
如果周围出现了值得采集的资源，即使并非目标，也可以进行搜集
会自动避开危险区域
{{
    "action_type":"mine_nearby",
    "name":"需要采集的方块名称",
    "count":"挖掘数量",
}}

**移动动作**
移动到一个能够到达的位置
{{
    "action_type":"move",
    "position": {{"x": x坐标, "y": y坐标, "z": z坐标}},
}}

**放置动作**
能够放置方块
{{
    "action_type":"place_block",
    "block":"方块名称",
    "position": {{"x": x坐标, "y": y坐标, "z": z坐标}},
}}

**退出采矿/采掘模式**
当你要进行其他动作，或进行其他操作，请退出采矿/采掘模式
{{
    "action_type":"exit_mining_mode",
}}

之前的思考和执行的记录：
{thinking_list}

**注意事项**
1.你当前正在采矿，请你先总结之前的思考和执行的记录，对执行结果进行分析，是否达成目的，是否需要调整任务或动作
2.你不仅要完成任务目标，还要注意搜集各种珍贵或有价值资源，包括但不限于：铁矿，金矿，钻石矿，煤炭，等等
2.当你要进行物品使用，熔炼，箱子，备忘录修改，任务修改等等动作时，请你退出采矿模式，进行其他动作
2.想法要求简短，精准，如果要描述坐标，完整的描述，不要有多余信息
3.然后根据现有的**动作**，**任务**,**情景**，**物品栏**,**最近事件**和**周围环境**，进行下一步规划，推进任务进度。
4.你的视野是周围3-4个方块，如果你需要更多信息，或者寻找目标，请移动到合适的位置，再进行规划
5.如果一个动作反复无法完成，请反思性思考，结合周围环境尝试别的方案，不要重复尝试同一个动作
规划内容是一段平文本，不要分点
规划后请使用动作，动作用json格式输出:
""",
            description="任务-动作选择",
            parameters=["goal", "task", "environment", "thinking_list", "nearby_block_info", "position", "memo_list", "chat_str"],
    ))




