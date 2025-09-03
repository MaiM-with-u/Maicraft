from agent.prompt_manager.prompt_manager import PromptTemplate, prompt_manager


def init_templates_learn_action() -> None:
    """初始化提示词模板"""

    
    prompt_manager.register_template(
        PromptTemplate(
        name="learn_action",
        template="""
请阅读下方的Python函数代码，生成关于这个函数的描述
1.应包含函数返回值类型和返回值内容
2.介绍函数能实现的功能
3.说明函数的适用场景

例如：

await bot.mine_block(x,y,z,digOnly: bool) -> tuple[bool,bool]:
描述：
#挖掘指定位置的方块，如果digOnly为True，则只挖掘方块，不收集掉落物
#x,y,z是方块的坐标
#返回值为tuple[bool,bool]，bool为是否成功，bool为位置是否存在方块或方块是否可以挖掘

await bot.get_block(x,y,z) -> Block:
描述：
# 获取指定位置的方块信息
# x,y,z是方块的坐标
# 返回值为Block类，方块信息
# 如果没有方块，返回None

await bot.chat(message) -> bool:
描述：
# 发送中文聊天消息
# message是聊天消息（中文
# 返回值为bool，为是否成功

代码如下：
```python
{code}
```
请你只输出描述文本，不要输出函数名，不要包含多余内容。只包含对函数的描述文本
""",
        description="学习动作",
        parameters=["code"],
    ))
    
    