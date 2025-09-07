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


**思考/执行的记录**
{thinking_list}


**检查熔炉**
在使用前，请你检查熔炉槽位，以正确使用熔炉：
检查熔炉当前input位的物品是否可以熔炼，如果是无法熔炼的物品，请取出，以免堵塞
检查熔炉当前fuel位的物品是否是有效燃料，如果不是有效燃料，请取出，并放入有效燃料
检查熔炉当前output位是否有产物，如果有，请及时取出

**注意事项**
1.请你根据之前的想法，对熔炉进行使用，存放和取出物品
2.请你先根据现有的**动作**，**任务**，**物品栏**,**最近事件**，进行下一步文本规划，然后输出动作json，你可以输出多个动作
规划内容是一段精简的平文本，不要分点
规划后请使用动作，动作用json格式输出，如果输出多个json，每个json都要单独用```json包裹:

**示例 - 多个动作：**
```json
{{
    "action_type": "take_items",
    "slot": "output",
    "item": "物品名称",
    "count": 2
}}
```

```json
{{
    "action_type": "put_items", 
    "slot": "fuel",
    "item": "物品名称",
    "count": 5
}}
```
""",
        description="熔炉使用",
        parameters=[
            "furnace_gui",
            "mode",
            "basic_info",
            "thinking_list", "nearby_block_info", "position", "chat_str"],
    ))
    