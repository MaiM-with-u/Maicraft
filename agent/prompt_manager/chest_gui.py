from agent.prompt_manager.prompt_manager import PromptTemplate, prompt_manager

def init_templates_chest_gui() -> None:
    """初始化提示词模板"""

    prompt_manager.register_template(
        PromptTemplate(
        name="chest_gui",
        template="""
{basic_info}
        
{chest_gui}

你可以进行如下操作：
**take_items**
从箱子中取出物品
{{
    "action_type":"take_items",
    "item":"需要取出的物品名称",
    "count":"数量",
}}

**put_items**
将物品放入箱子
{{
    "action_type":"put_items",
    "item":"需要放入的物品名称",
    "count":"数量",
}}

**思考/执行的记录**
{thinking_list}


**注意事项**
1.请你根据之前的想法，对箱子进行使用，存放和取出物品
2.你可以进行多次存入和取出物品，可以一次性输出多个动作
3.如果需要执行多个存取动作，请按顺序列出所有动作，系统会依次执行每个动作，每个动作间等待0.3秒
规划内容是一段精简的平文本，不要分点
规划后请使用动作，动作用json格式输出，如果输出多个json，每个json都要单独用```json包裹:

**示例 - 多个动作：**
```json
{{
    "action_type": "take_items",
    "item": "物品名称",
    "count": 2
}}
```

```json
{{
    "action_type": "put_items", 
    "item": "物品名称",
    "count": 5
}}
```
""",
        description="箱子面板",
        parameters=[
            "chest_gui",
            "basic_info",
            "thinking_list", "nearby_block_info", "position", "chat_str"],
    ))
    