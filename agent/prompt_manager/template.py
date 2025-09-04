from agent.prompt_manager.prompt_manager import PromptTemplate, prompt_manager
from agent.prompt_manager.template_chat import init_templates_chat
from agent.prompt_manager.chest_gui import init_templates_chest_gui
from agent.prompt_manager.furnace_gui import init_templates_furnace_gui
from agent.prompt_manager.template_task import init_templates_task

def init_templates() -> None:
    """初始化提示词模板"""
    init_templates_chat()
    init_templates_task()
    init_templates_chest_gui()
    init_templates_furnace_gui()
    
    prompt_manager.register_template(
        PromptTemplate(
        name="basic_info",
        template="""
你是麦麦，游戏名叫Mai,你正在游玩Minecraft，是一名Minecraft玩家。
{self_info}

**当前目标和任务列表**：
目标：{goal}
任务列表：
{to_do_list}

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
""",
        description="基础信息",
        parameters=[
            "self_info",
            "mode",
            "goal",
            "event_str",
            "task",
            "environment",
            "nearby_block_info",
            "position",
            "chat_str",
            "to_do_list"],
    ))
    
    

    prompt_manager.register_template(
        PromptTemplate(
        name="main_thinking",
        template="""
{basic_info}

**动作**
**break_block**
挖掘某个位置指定的方块
1.可选择挖掘指定位置的方块，使用type = "position"，只会挖掘xyz指定的方块
2.可选挖掘附近count个name类型的方块，使用type = "nearby"，会自动寻找并挖掘附近count个name类型的方块，不需要额外使用move
{{
    "action_type":"break_block",
    "type":"挖掘类型(必选)",
    "name":"挖掘方块名称（可选）",
    "count":"挖掘数量（可选）",
    "x":"挖掘x位置(可选)",
    "y":"挖掘y位置(可选)",
    "z":"挖掘z位置(可选)",
    "digOnly":"是否只挖掘，如果为True，则不收集方块（可选，默认为True）",
}}

**place_block**
能够放置方块到xyz指定位置
{{
    "action_type":"place_block",
    "block":"方块名称",
    "x":"放置x位置",
    "y":"放置y位置",
    "z":"放置z位置",
}}

**move**
移动到一个能够到达的位置，如果已经到达，则不需要移动
{{
    "action_type":"move",
    "position":{{"x": x坐标, "y": y坐标, "z": z坐标}},
}}

**craft**
使用工作台或者背包进行合成物品
能够进行工作台3x3合成
能够进行直接2x2合成
{{
    "action_type":"craft",
    "item":"物品名称",
    "count":"数量"
}}

**use_furnace**
打开熔炉，可以熔炼或取出熔炼的物品
{{
    "action_type":"use_furnace",
    "position":{{"x": x坐标, "y": y坐标, "z": z坐标}}
}}

**use_chest**
打开chest，将物品放入箱子或从箱子中取出物品
你可以存入或取出多种物品
{{
    "action_type":"use_chest",
    "position":{{"x": x坐标, "y": y坐标, "z": z坐标}},
}}
 
{eat_action}

**use_item**
使用某样物品，可以对实体使用物品
注意，如果是使用方块或放置方块，不要使用此动作
如果要对实体使用物品，如剪刀对sheep，请填写entity，否则不要填写entity
{{
    "action_type":"use_item",
    "item":"需要使用的物品名称",
    "entity":"需要对其使用的实体名称",
}}

**设置标记点**
记录一个标记点/地标，可以记录重要位置的信息，用于后续的移动，采矿，探索等
{{
    "action_type":"set_location",
    "name":"地标名称（不要与现有地标名称重复）",
    "info":"地标信息，描述和简介",
    "position":{{"x": x坐标, "y": y坐标, "z": z坐标}},
}}

**前往地标**
前往指定的地标，尝试移动到名为name的坐标点
{{
    "action_type":"go_to_location",
    "name":"地标名称",
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

**思考/执行的记录**
{thinking_list}


**注意事项**
1.先总结之前的思考和执行的记录，对执行结果进行分析，是否达成目的，是否需要调整任务或动作
2.你必须先查看容器的内容物，才能与容器交互
3.想法要求准确全面，如果要描述坐标，完整的描述
4.如果要修改任务列表，请你进入task_edit模式
4.你可以通过事件知道别的玩家的位置，或者别的玩家正在做什么。
5.然后根据现有的**动作**，**任务**,**情景**，**物品栏**,**最近事件**和**周围环境**，进行下一步规划，推进任务进度。
6.如果一个动作反复无法完成，请反思性思考，结合周围环境尝试别的方案，不要重复尝试同一个动作
7.如果一个动作已经执行，并且达到了目的，请不要重复执行同一个动作
规划内容是一段精简的平文本，不要分点
规划后请使用动作，动作用json格式输出:
""",
        description="任务-动作选择",
        parameters=[
            "mode",
            "goal","event_str","task", "environment", "thinking_list", "nearby_block_info", "position", "chat_str", "basic_info","eat_action"],
    ))
    