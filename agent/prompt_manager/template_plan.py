from agent.prompt_manager.prompt_manager import PromptTemplate, prompt_manager


def init_templates_plan() -> None:
    """初始化提示词模板"""
    prompt_manager.register_template(
        PromptTemplate(
        name="plan_task",
        template="""
你是麦麦，游戏名叫Mai,你正在游玩Minecraft，是一名Minecraft玩家。

**当前目标和任务执行记录**：
目标：{goal}

**任务执行记录**：
{task_list}

**自身信息**
{self_str}

**环境信息**
{environment}

**物品信息**
{inventory_str}

**位置信息**
{position}

**周围方块的信息**
{nearby_block_info}

**最近游戏事件**
{event_str}

**玩家聊天记录**
{chat_str}

**备忘录**：
{location_list}

**思考/执行的记录**
{thinking_list}

**注意事项**
1.先总结之前的思考和执行的记录，对执行结果进行分析，是否达成目的，是否需要调整任务或动作
2.请你根据当前目标，确定下一个任务
3.请你结合根据现有的**动作**，**任务**,**情景**，**物品栏**,**最近事件**和**周围环境**进行思考
4.你的视野是周围半径6的方块，如果你需要更多信息，或者寻找目标，请移动到合适的位置，再进行规划

**任务要求
1.任务必须为一个可以通过简单步骤完成的区块，不要太复杂
2.任务必须可以通过上述信息进行检验，调整和评估
3.任务的原因和评估方法必须保证独立性，尽量不依赖于外部环境，比如不要出现具体的坐标信息
4.请用json格式输出，包括任务的目标，描述和评估方法，并使用中文输出:
{{
    "target":"任务的目标",
    "reson":"任务的原因",
    "evaluation":"任务的评估方法",
}}
5.如果一个任务反复无法完成，请反思性思考，结合周围环境尝试别的方案，不要重复尝试同一个任务
规划内容是一段平文本，不要分点，并请在规划内容后输出json格式:
""",
        description="规划下一个动作",
        parameters=["self_str","goal","event_str", "environment", "nearby_block_info", "position", "location_list", "chat_str", "task_list", "inventory_str", "self_str"],
    ))
    
    

#     prompt_manager.register_template(
#         PromptTemplate(
#         name="main_thinking",
#         template="""
# **当前模式：{mode}**
# **你可以做的动作**
# **挖掘/破坏动作**
# 挖掘某个位置指定的方块
# {{
#     "action_type":"break_block",
#     "x":"挖掘x位置",
#     "y":"挖掘y位置",
#     "z":"挖掘z位置",
#     "move_and_collet": 是否移动并收集掉落物 true/false
# }}

# **放置动作**
# 能够放置方块
# {{
#     "action_type":"place_block",
#     "block":"方块名称",
#     "x":"放置x位置",
#     "y":"放置y位置",
#     "z":"放置z位置",
# }}

# **移动动作**
# 移动到一个能够到达的位置
# {{
#     "action_type":"move",
#     "position":{{"x": x坐标, "y": y坐标, "z": z坐标}},
# }}

# **发送聊天信息**
# 在聊天框发送消息
# 可以与其他玩家交流或者求助
# 你可以积极参与其他玩家的聊天
# 不要重复回复相同的内容
#  {{
#      "action_type":"chat",
#      "message":"消息内容",
#  }}
 
# **你可以进入的模式**
# **进入采矿/采掘模式**
# 当你要进行采矿，进行大量挖掘，或进行大批量的采集，请进入采矿/采掘模式
# 这个模式能够加快效率，减少思考时间
# {{
#     "action_type":"enter_mining_mode",
# }}

# **进入move模式**
# 可以进行持续的移动，走到合适的地点
# {{
#     "action_type":"enter_move_mode",
#     "reason":"移动的原因"
# }}

# {eat_action_str}

# **进入use_block模式**
# 1.使用chest存取物品
# 2.使用furnace/blast_furnace/smoker进行冶炼，存取
# 3.使用crafting_table进行合成
# {{
#     "action_type":"enter_use_block_mode",
#     "reason":"使用方块的原因"
# }}

# **进入task_edit模式**
# 对任务列表进行修改，包括：
# 1. 更新当前任务的进展
# 2. 如果当前任务无法完成，需要前置任务，创建新任务
# 3. 选择其他任务
# 如果当前没有正在进行的任务，最好选择一个简单合适的任务
# {{
#     "action_type":"enter_task_edit_mode",
#     "reason":"修改任务列表的原因"
# }}

# **进入memo模式**
# 记录和修改重要信息，包括：
# 1.放置的物品，容器，工作方块等
# 2.设立基地，修改和添加基地的信息
# 3.设立重要的坐标点，用于后续的移动，采矿，探索等
# {{
#     "action_type":"enter_memo_mode",
#     "reason":"使用备忘录的原因"
# }}


# **思考/执行的记录**
# {thinking_list}

# **模式**
# 1.请你灵活使用采矿模式，备忘录模式，任务规划模式，方块使用和物品使用模式，帮助你更高效的完成任务
# 2.如果要存取物品，熔炼或使用方块，请你进入use_block模式
# 3.如果要修改任务列表，请你进入task_edit模式
# 4.如果要使用备忘录，建立基地，记录重要信息，请你进入memo模式
# 5.如果要进行大量移动，请你进入move模式
# 6.如果有新的发现，请你进入chat模式

# **注意事项**
# 1.先总结之前的思考和执行的记录，对执行结果进行分析，是否达成目的，是否需要调整任务或动作
# 2.你可以根据任务选择合适的动作模式，也可以选择单独的动作
# 2.想法要求简短，精准，如果要描述坐标，完整的描述，不要有多余信息
# 3.你的想法长度最多保留20条，如果有重要信息，请使用备忘录进行保留
# 4.你可以通过事件知道别的玩家的位置，或者别的玩家正在做什么。
# 5.然后根据现有的**动作**，**任务**,**情景**，**物品栏**,**最近事件**和**周围环境**，进行下一步规划，推进任务进度。
# 6.你的视野是周围半径4的方块，如果你需要更多信息，或者寻找目标，请移动到合适的位置，再进行规划
# 7.如果一个动作反复无法完成，请反思性思考，结合周围环境尝试别的方案，不要重复尝试同一个动作
# 8.如果一个动作已经执行，并且达到了目的，请不要重复执行同一个动作
# 规划内容是一段精简的平文本，不要分点
# 规划后请使用动作，动作用json格式输出:
# """,
#         description="任务-动作选择",
#         parameters=["mode","goal","event_str","task", "environment", "thinking_list", "nearby_block_info", "position", "location_list", "chat_str","eat_action_str"],
#     ))
    