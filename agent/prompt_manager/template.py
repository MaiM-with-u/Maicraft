from agent.prompt_manager.prompt_manager import PromptTemplate, prompt_manager
from agent.prompt_manager.template_place import init_templates_place
from agent.prompt_manager.template_mining import init_templates_mining
from agent.prompt_manager.template_use_block import init_templates_use_block
from agent.prompt_manager.template_move import init_templates_move
from agent.prompt_manager.template_memo import init_templates_memo

def init_templates() -> None:
    """初始化提示词模板"""
    init_templates_place()
    init_templates_mining()
    init_templates_use_block()
    init_templates_move()
    init_templates_memo()

    prompt_manager.register_template(
        PromptTemplate(
        name="minecraft_excute_task_thinking",
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

**当前模式：{mode}**
**你可以做的动作**
**聊天动作**
在聊天框发送消息
可以与其他玩家交流或者求助
你可以积极参与其他玩家的聊天
 {{
     "action_type":"chat",
     "message":"消息内容",
 }}
 
**挖掘/破坏动作**
挖掘某个位置指定的方块
{{
    "action_type":"break_block",
    "x":"挖掘x位置",
    "y":"挖掘y位置",
    "z":"挖掘z位置",
}}

**进入采矿/采掘模式**
当你要进行采矿，进行大量挖掘，或进行大批量的采集，请进入采矿/采掘模式
这个模式能够加快效率，减少思考时间
{{
    "action_type":"enter_mining_mode",
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

**进入移动模式**
可以进行持续的移动，走到合适的地点
{{
    "action_type":"enter_move_mode",
    "reason":"移动的原因"
}}

**进入使用方块模式**
可以打开chest存取物品，打开furnace进行冶炼，或存取熔炼后的物品
或者使用crafting_table等功能性方块进行合成等操作
{{
    "action_type":"enter_use_block_mode",
    "reason":"使用方块的原因"
}}

**进入任务规划模式**
对任务列表进行修改，包括：
1. 更新当前任务的进展
2. 如果当前任务无法完成，需要前置任务，创建新任务
3. 选择其他任务
{{
    "action_type":"enter_task_edit_mode",
    "reason":"修改任务列表的原因"
}}

**进入备忘录模式**
记录重要信息，用于后续思考和执行
{{
    "action_type":"enter_memo_mode",
    "reason":"使用备忘录的原因"
}}


之前的思考和执行的记录：
{thinking_list}

**模式**
1.请你灵活使用采矿模式，备忘录模式，任务规划模式，帮助你更高效的完成任务
2.如果要存取物品，熔炼或使用方块，请你进入使用方块模式
3.如果要修改任务列表，请你进入任务规划模式
4.如果要使用备忘录，请你进入备忘录模式
5.如果要进行大量移动，请你进入移动模式

**注意事项**
1.先总结之前的思考和执行的记录，对执行结果进行分析，是否达成目的，是否需要调整任务或动作
2.你可以根据任务选择合适的动作模式，也可以选择单独的动作
2.想法要求简短，精准，如果要描述坐标，完整的描述，不要有多余信息
3.你的想法长度最多保留20条，如果有重要信息，请使用备忘录进行保留
4.你可以通过事件知道别的玩家的位置，或者别的玩家正在做什么。
5.然后根据现有的**动作**，**任务**,**情景**，**物品栏**,**最近事件**和**周围环境**，进行下一步规划，推进任务进度。
6.你的视野是周围3-4个方块，如果你需要更多信息，或者寻找目标，请移动到合适的位置，再进行规划
7.如果一个动作反复无法完成，请反思性思考，结合周围环境尝试别的方案，不要重复尝试同一个动作
8.如果一个动作已经执行，并且达到了目的，请不要重复执行同一个动作
规划内容是一段精简的平文本，不要分点
规划后请使用动作，动作用json格式输出:
""",
        description="任务-动作选择",
        parameters=["mode","goal", "task", "environment", "thinking_list", "nearby_block_info", "position", "memo_list", "chat_str"],
    ))
    
    
    prompt_manager.register_template(
        PromptTemplate(
        name="minecraft_excute_task_action",
        template="""
你是麦麦，游戏名叫Mai,你正在游玩Minecraft，是一名Minecraft玩家。请你选择合适的动作修改当前的任务列表：
**当前目标**：
{goal}

**当前任务列表**：
{to_do_list}

**任务执行记录**：
{task_done_list}

**当前正在执行的任务**：
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
 
**动作列表：任务规划动作**
1. 更新某个未完成的任务的进度
 {{
     "action_type":"update_task_progress",
     "task_id":"任务id",
     "progress":"如果任务未完成，请更新目前任务的进展情况",
     "done":bool类型，true表示完成，false表示未完成
 }}
 
 2. 如果当前任务无法完成，需要前置任务，创建一个新任务:
 {{
     "action_type":"create_new_task",
     "new_task":"前置任务的描述",
     "new_task_criteria":"前置任务的评估标准",
 }}
 
 3. 如果当前条件适合执行别的任务，或当前任务无法完成，需要更换任务，请选择一个合适的任务:
 如果当前没有在执行任务，请选择一个合适的任务
 {{
     "action_type":"change_task",
     "new_task_id":"任务id",
 }}
 
 4. 如果某个任务是无法完成，不合理的，请删除该任务
 {{
     "action_type":"delete_task",
     "task_id":"任务id",
     "reason":"删除任务的原因",
 }}
 

 
 之前的思考和执行的记录：
{thinking_list}

**注意事项**
1.先总结之前的思考和执行的记录，对执行结果进行分析，是否达成目的，是否需要调整任务或动作
2.然后根据现有的**动作**，**任务**,**情景**，**物品栏**和**周围环境**，进行下一步规划，推进任务进度。
规划内容是一段平文本，不要分点
规划后请使用动作，你**必须**从上述动作列表中选择一个动作，动作用json格式输出:
""",
        description="任务-任务动作",
        parameters=["goal", "to_do_list", "task_done_list", "task", "environment", "thinking_list", "nearby_block_info", "position", "memo_list", "chat_str"],
    ))
    
    
    
    
    prompt_manager.register_template(
        PromptTemplate(
        name="minecraft_to_do",
        template="""
你是麦麦，游戏名叫Mai,你正在游玩Minecraft，是一名Minecraft玩家。请根据当前的目标，来决定要做哪些事：

**当前目标**：{goal}

**位置信息**：
{position}

**环境信息**：
{environment}

**周围方块的信息**：
{nearby_block_info}

**玩家聊天记录**：
{chat_str}

请判断为了达成目标，需要进行什么任务
请列举出所有需要完成的任务，并以json格式输出：

注意，任务的格式如下，请你参考以下格式：
{{
    "tasks": {{
    {{
        "details":"挖掘十个石头,用于合成石稿",
        "done_criteria":"物品栏中包含十个及以上石头"
    }},
    {{
        "type": "craft",
        "details":"使用工作台合成一把石稿,用于挖掘铁矿",
        "done_criteria":"物品栏中包含一把石稿"
    }},
    {{
        "type": "move",
        "details":"移动到草地,用于挖掘铁矿",
        "done_criteria":"脚下方块为grass_block"
    }},
    {{
        "type": "place",
        "details":"在面前放置一个熔炉,用于熔炼铁锭",
        "done_criteria":"物品栏中包含一个熔炉"
    }},
    {{
        "type": "get",
        "details":"从箱子里获取三个铁锭,用于合成铁桶",
        "done_criteria":"物品栏中包含三个铁锭"
    }}
    }}
}}

*请你根据当前的物品栏，环境信息，位置信息，来决定要如何安排任务*

你可以：
1. 任务需要明确，并且可以检验是否完成
2. 可以一次输出多个任务，保证能够达成目标

请用json格式输出任务列表。
""",
        description="任务规划",
        parameters=["goal", "environment", "nearby_block_info", "position", "chat_str"],
    ))
    