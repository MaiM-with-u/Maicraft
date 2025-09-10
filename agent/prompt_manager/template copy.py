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

**物品栏和工具**
{inventory_info}

**位置信息**
{position}

**周围方块的信息**
{nearby_block_info}

**周围箱子信息**
{container_cache_info}

**周围实体信息**
{nearby_entities_info}

**玩家聊天记录**
{chat_str}
""",
        description="基础信息",
        parameters=[
            "nearby_entities_info",
            "self_info",
            "mode",
            "goal",
            "task",
            "environment",
            "nearby_block_info",
            "position",
            "chat_str",
            "to_do_list",
            "container_cache_info",
            "inventory_info"],
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
    "type":"position",
    "x":"挖掘x位置(可选)",
    "y":"挖掘y位置(可选)",
    "z":"挖掘z位置(可选)",
    "digOnly":"是否只挖掘，如果为True，则不收集方块（可选，默认为True）",
}}

{{
    "action_type":"break_block",
    "type":"nearby",
    "name":"挖掘方块名称（可选）",
    "count":"挖掘数量（可选）",
}}

**place_block**
能够放置方块到xyz指定位置
你只能放置在可以放置的坐标上
{{
    "action_type":"place_block",
    "block":"方块名称",
    "x":"放置x位置",
    "y":"放置y位置",
    "z":"放置z位置",
}}

**move**
移动到一个能够到达的位置，如果已经到达，则不需要移动
请选择可以移动的位置
{{
    "action_type":"move",
    "position":{{"x": x坐标, "y": y坐标, "z": z坐标}},
}}

**find_block**
在视野内寻找可以直接看见的指定方块，返回方块的位置
{{
    "action_type":"find_block",
    "radius": 8 //视野范围，默认8半径
    "block":"方块名称",
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

**kill_mob**
杀死某个实体
杀死动物，怪物或玩家
{{
    "action_type":"kill_mob",
    "entity":"需要杀死的实体名称",
    "timeout":"杀死实体的超时时间，单位：秒",
}}

**设置标记点**
记录一个标记点/地标，可以记录重要位置的信息
也可以删除一个不符合现状的地表
也可以update地标信息
{{
    "action_type":"set_location",
    "type":"set/delete/update", //set表示设置，delete表示删除，update表示更新
    "name":"地标名称（不要与现有地标名称重复）",
    "info":"地标信息，描述和简介",
    "position":{{"x": x坐标, "y": y坐标, "z": z坐标}},
}}

**进入task_edit模式**
对任务列表进行修改，包括：
1. 更新当前任务的进展
2. 如果当前任务无法完成，需要前置任务，创建新任务
3. 选择其他任务
如果当前没有正在进行的任务，最好选择一个简单合适的任务
{{
    "action_type":"edit_task_list",
}}

**思考/执行的记录**
{thinking_list}


**行为准则**
1.先总结之前的思考和执行的记录，对执行结果进行分析，上一次使用的动作是否达到了目的
2.如果目的已达成，进行下一轮动作。如果目的未达成，根据结果进行修正。
3.如果一个动作反复无法完成，可能是参数错误或缺少必要条件，请结合周围环境尝试别的方案，不要重复尝试同一个动作
4.你不需要搭建方块来前往某个地方，直接使用move动作，会自动搭建并移动
5.task_edit可以帮助你规划当前任务并保持专注。
6.set_location可以帮助你记录重要位置的信息，用于后续的移动，采矿，探索等

**游戏指南**
1.当你收集或挖掘一种资源，搜索一下附近是否有遗漏的同类资源，尽可能采集
2.提前准备好食物，工具，建材等常备物资再进行活动
3.根据你的**位置信息**和**周围方块信息**，评估现在所处的环境：建筑物/洞穴/矿道/地面/森林/冰原/沙漠/水体......
4.不同的环境拥有不同的资源，你需要根据当前目的进行移动和搜集资源
5.请思考你的移动方向，你可以在y轴上下移动来前往地面，地下和不同的高度。

**输出**
现在请你根据现有的**动作**，**任务**,**情景**，**物品栏**,**最近事件**和**周围环境**，进行下一步规划，推进任务进度。
规划内容是一段文本，不要分点。规划后请使用动作，动作用json格式输出，如果输出多个json，每个json都要单独用```json包裹，你可以重复使用同一个动作或不同动作:

**示例**
//规划的文字内容
```json
{{
    "action_type":"move",
    "position":{{"x": x坐标, "y": y坐标, "z": z坐标}},
}}
```
```json
{{
    "action_type":"use_chest",
    "position":{{"x": x坐标, "y": y坐标, "z": z坐标}},
}}
```
""",
        description="任务-动作选择",
        parameters=[
            "thinking_list", "nearby_block_info", "position", "chat_str", "basic_info","eat_action"],
    ))
    
    
    
# ?暂时没想好怎么处理合成，因为合成还要考虑2x2的  
# **use_block**
# 使用方块，目前可以使用的方块：
# chest:存入或取出物品，可以存入或取出多种物品
# furnace:熔炼物品，可以熔炼或取出熔炼的物品
# crafting_table:合成物品，可以合成多种物品
# {{
#     "action_type":"use_block",
#     "block":"方块名称",
#     "position":{{"x": x坐标, "y": y坐标, "z": z坐标}},
# }}