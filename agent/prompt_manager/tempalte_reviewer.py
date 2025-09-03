from agent.prompt_manager.prompt_manager import PromptTemplate, prompt_manager

def init_templates_reviewer() -> None:
    """初始化提示词模板"""

    prompt_manager.register_template(
        PromptTemplate(
            name="reviewer",
            template="""
你需要编写程序来完成一个Minecraft游戏任务：
<task>
{task}
</task>

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

程序的结果输出：
{output_last_run}


现在请你分析任务的执行结果，是否完成task任务目标，请用json格式输出结果：
如果完成，则success为true，并输出理由
如果未完成，则success为false，并输出理由
{{
  "success": bool,
  "reason": str
}}
请你输出json，不要输出其他内容
""",
            description="代码审查",
            parameters=["self_str","event_str","chat_str","location_list","game_info_before","game_info_after","output_last_run","goal", "task", "environment", "thinking_list", "nearby_block_info", "position", "location_list", "chat_str", "inventory_str"],
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