from agent.prompt_manager.prompt_manager import PromptTemplate, prompt_manager

def init_templates_reviewer() -> None:
    """初始化提示词模板"""

    prompt_manager.register_template(
        PromptTemplate(
            name="reviewer",
            template="""
你需要编写程序来完成一个Minecraft游戏任务：
{task}

**自身信息**
{self_str}
-------------------
以下是任务开始前，你的状态信息：
{game_info_before}
-------------------
以下是任务执行后的状态信息：
{game_info_after}
-------------------
**最近游戏事件**
{event_str}

**玩家聊天记录**
{chat_str}

**坐标点信息**：
{location_list}
--------------------
运行程序
{code_last_run}

程序的结果输出：
{output_last_run}


现在请你分析任务的执行结果，是否完成task任务目标，请用json格式输出结果：
如果完成，则success为true
如果未完成，则success为false
评估标准
1.分清任务的主要目的和具体标准，不用太严格的判定，同时遵循二八定律，完成80%以上就算完成
2.如果任务没有达到目的，进行反思性的思考，考虑程序的问题，并提出修改建议，写入suggestion
3.请你考虑当前所在位置和周围环境，是否能够完成任务，并根据当前环境内容对程序提出修改意见
{{
  "success": bool,
  "reason": str
  "suggestion": str
  "change_task": false
}}
4.如果多次尝试无法完成当前任务，需要更改任务，请将change_task设置为true，并输出原因和建议
{{
    "change_task": true,
    "success": false,
    "reason": str
    "suggestion": str
}}
请你输出json，不要输出其他内容
""",
            description="代码审查",
            parameters=["self_str","event_str","chat_str","location_list","game_info_before","game_info_after","output_last_run","goal", "task", "environment", "thinking_list", "nearby_block_info", "position", "location_list", "chat_str", "inventory_str", "code_last_run"],
        )
    )
    
    
    prompt_manager.register_template(
        PromptTemplate(
            name="game_info",
            template="""
**环境信息**
{environment}

**物品信息**
{inventory_str}

**位置信息**
{position}

**周围方块的信息**
{nearby_block_info}

""",
            description="游戏信息",
            parameters=["retrieved_skills","code_last_run","error_last_run","event_str","goal", "task", "environment", "thinking_list", "nearby_block_info", "position", "location_list", "chat_str", "inventory_str"],
        )
    )