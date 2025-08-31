from agent.prompt_manager.prompt_manager import PromptTemplate, prompt_manager
from agent.prompt_manager.template_place import init_templates_place
from agent.prompt_manager.template_mining import init_templates_mining
from agent.prompt_manager.template_use_block import init_templates_use_block
from agent.prompt_manager.template_move import init_templates_move
from agent.prompt_manager.template_memo import init_templates_memo
from agent.prompt_manager.template_chat import init_templates_chat
from agent.prompt_manager.template_use_item import init_templates_use_item
from agent.prompt_manager.template_task import init_templates_task

def init_templates() -> None:
    """初始化提示词模板"""
    init_templates_place()
    init_templates_mining()
    init_templates_use_block()
    init_templates_move()
    init_templates_memo()
    init_templates_chat()
    init_templates_use_item()
    init_templates_task()
    
    prompt_manager.register_template(
        PromptTemplate(
        name="basic_info",
        template="""
你是麦麦，游戏名叫Mai,你正在游玩Minecraft，是一名Minecraft玩家。

**当前目标和任务列表**：
目标：{goal}
{to_do_list}

当前选择的任务：
{task}

**环境信息**
{environment}

**位置信息**
{position}

**周围方块的信息**
{nearby_block_info}

**最近游戏事件**
{event_str}

**玩家聊天记录**
{chat_str}

**备忘录**：
{memo_list}
""",
        description="基础信息",
        parameters=["mode","goal","event_str","task", "environment", "nearby_block_info", "position", "memo_list", "chat_str", "to_do_list"],
    ))
    
    

    prompt_manager.register_template(
        PromptTemplate(
        name="main_thinking",
        template="""
**当前模式：{mode}**
**你可以做的动作**
**挖掘/破坏动作**
挖掘某个位置指定的方块
{{
    "action_type":"break_block",
    "x":"挖掘x位置",
    "y":"挖掘y位置",
    "z":"挖掘z位置",
}}

**放置动作**
能够放置方块
{{
    "action_type":"place_block",
    "block":"方块名称",
    "x":"放置x位置",
    "y":"放置y位置",
    "z":"放置z位置",
}}

**移动动作**
移动到一个能够到达的位置
{{
    "action_type":"move",
    "position":{{"x": x坐标, "y": y坐标, "z": z坐标}},
}}

**发送聊天信息**
在聊天框发送消息
可以与其他玩家交流或者求助
你可以积极参与其他玩家的聊天
不要重复回复相同的内容
 {{
     "action_type":"chat",
     "message":"消息内容",
 }}
 
**你可以进入的模式**
**进入采矿/采掘模式**
当你要进行采矿，进行大量挖掘，或进行大批量的采集，请进入采矿/采掘模式
这个模式能够加快效率，减少思考时间
{{
    "action_type":"enter_mining_mode",
}}

**进入move模式**
可以进行持续的移动，走到合适的地点
{{
    "action_type":"enter_move_mode",
    "reason":"移动的原因"
}}

**进入use_item模式**
可以使用背包中的物品，但是你只能使用以下物品
1.食用食物
2.可激活的物品，例如药水等
3.可对实体使用的物品，例如剪刀，栓绳等
{{
    "action_type":"enter_use_item_mode",
    "reason":"使用物品的原因"
}}

**进入use_block模式**
可以打开chest存取物品，打开furnace进行冶炼，或存取熔炼后的物品
或者使用crafting_table等功能性方块进行合成等操作
{{
    "action_type":"enter_use_block_mode",
    "reason":"使用方块的原因"
}}

**进入task_edit模式**
对任务列表进行修改，包括：
1. 更新当前任务的进展
2. 如果当前任务无法完成，需要前置任务，创建新任务
3. 选择其他任务
如果当前没有正在进行的任务，最好选择一个简单合适的任务
{{
    "action_type":"enter_task_edit_mode",
    "reason":"修改任务列表的原因"
}}

**进入memo模式**
记录和修改重要信息，包括：
1.放置的物品，容器，工作方块等
2.设立基地，修改和添加基地的信息
3.设立重要的坐标点，用于后续的移动，采矿，探索等
{{
    "action_type":"enter_memo_mode",
    "reason":"使用备忘录的原因"
}}


**思考/执行的记录**
{thinking_list}

**模式**
1.请你灵活使用采矿模式，备忘录模式，任务规划模式，方块使用和物品使用模式，帮助你更高效的完成任务
2.如果要存取物品，熔炼或使用方块，请你进入use_block模式,而不是进入use_item模式
3.如果要使用物品，请你进入use_item模式,而不是进入use_block模式
4.如果要修改任务列表，请你进入task_edit模式
5.如果要使用备忘录，建立基地，记录重要信息，请你进入memo模式
6.如果要进行大量移动，请你进入move模式
7.如果有新的发现，请你进入chat模式

**注意事项**
1.先总结之前的思考和执行的记录，对执行结果进行分析，是否达成目的，是否需要调整任务或动作
2.你可以根据任务选择合适的动作模式，也可以选择单独的动作
2.想法要求简短，精准，如果要描述坐标，完整的描述，不要有多余信息
3.你的想法长度最多保留20条，如果有重要信息，请使用备忘录进行保留
4.你可以通过事件知道别的玩家的位置，或者别的玩家正在做什么。
5.然后根据现有的**动作**，**任务**,**情景**，**物品栏**,**最近事件**和**周围环境**，进行下一步规划，推进任务进度。
6.你的视野是周围半径4的方块，如果你需要更多信息，或者寻找目标，请移动到合适的位置，再进行规划
7.如果一个动作反复无法完成，请反思性思考，结合周围环境尝试别的方案，不要重复尝试同一个动作
8.如果一个动作已经执行，并且达到了目的，请不要重复执行同一个动作
规划内容是一段精简的平文本，不要分点
规划后请使用动作，动作用json格式输出:
""",
        description="任务-动作选择",
        parameters=["mode","goal","event_str","task", "environment", "thinking_list", "nearby_block_info", "position", "memo_list", "chat_str"],
    ))
    