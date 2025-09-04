from agent.prompt_manager.prompt_manager import PromptTemplate, prompt_manager

def init_templates_furnace_gui() -> None:
    """初始化提示词模板"""

    prompt_manager.register_template(
        PromptTemplate(
        name="furnace_gui",
        template="""
{basic_info}    
    
{furnace_gui}

你可以进行如下操作：
**take_items**
从槽位中取出物品
{{
    "action_type":"take_items",
    "slot":"input/fuel/output", //操作的槽位，input表示原料，fuel表示燃料，output表示产物
    "item":"需要取出的物品名称",
    "count":"数量",
}}

**put_items**
将物品放入槽位
{{
    "action_type":"put_items",
    "slot":"input/fuel/output", //操作的槽位，input表示原料，fuel表示燃料，output表示产物
    "item":"需要放入的物品名称",
    "count":"数量",
}}
 

关闭熔炉
**exit_furnace_gui**
关闭熔炉界面，使用其他动作
结束熔炉使用
{{
    "action_type":"exit_furnace_gui",
}}

**思考/执行的记录**
{thinking_list}


**注意事项**
1.请你根据之前的想法，对熔炉进行使用，存放和取出物品
2.请判断熔炉当前input位的物品是否可以熔炼，fuel是否是有效燃料
3.如果有output位物品没有被拿出，占用了位置，请先拿出
4.当取用完毕后，使用exit_furnace_gui动作关闭熔炉界面，使用其他动作
5.然后根据现有的**动作**，**任务**,**情景**，**物品栏**,**最近事件**和**周围环境**，进行下一步规划，推进任务进度。
规划内容是一段精简的平文本，不要分点
规划后请使用动作，动作用json格式输出，一次输出一个动作:
""",
        description="熔炉使用",
        parameters=[
            "furnace_gui",
            "mode",
            "basic_info",
            "goal","event_str","task", "environment", "thinking_list", "nearby_block_info", "position", "chat_str"],
    ))
    