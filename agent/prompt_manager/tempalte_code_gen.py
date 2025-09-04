from agent.prompt_manager.prompt_manager import PromptTemplate, prompt_manager

def init_templates_code_gen() -> None:
    """初始化提示词模板"""

    prompt_manager.register_template(
        PromptTemplate(
            name="code_generate",
            template="""
你需要编写程序来完成一个Minecraft游戏任务：
{task}

你需要使用给出的API编写python程序，完成给出的指定任务
以下是你可以使用的APIs:

#bot物品栏
await bot.inventory：List[Item]，bot拥有的所有物品列表

#bot 的坐标位置
await bot.position: BlockPosition, bot当前位置

Item类包含：
name: str
count: int
durability: int
max_durability: int

Block类包含：
block_type: str
position: BlockPosition
#block_type为air时，表示此处没有方块

BlockPosition类包含：
x: int
y: int
z: int

await bot.mine_block(x,y,z,digOnly: bool) -> tuple[bool,bool]:
#挖掘指定位置的方块，如果digOnly为True，则只挖掘方块，不收集掉落物
#会自动使用对应工具进行挖掘，不需要手动切换
#x,y,z是方块的坐标
#返回值为tuple[bool,bool]，bool为是否成功，bool为位置是否存在方块或方块是否可以挖掘

await bot.place_block(block, x,y,z) -> tuple[bool,bool]:
# 放置背包中的指定方块到指定位置
# 会自动选择背包中的指定方块，不需要手动选择
# block是方块的名称
# x,y,z是方块的坐标
# 返回值为tuple[bool,bool]，bool为是否成功，bool为位置是否存在方块或实体

await bot.find_blocks(block_type, radius) -> tuple[bool,list[Block]]:
# 自动寻找附近视野可见的或见过的某种方块，返回方块位置列表
# block_type是方块的名称
# radius是搜索半径，最大64格
# 返回值为tuple[bool,list[Block]]，bool为是否成功，list[Block]为方块列表，list[Block]会将距离当前位置最近的方块排在前面

await bot.get_block(x,y,z) -> Block|None:
# 获取指定位置的方块信息
# x,y,z是方块的坐标
# 返回值为Block类，方块信息
# 如果Block类型为air，则代表此处没有方块
# 如果此处方块未知，返回None

await bot.craft_item(item, count) -> tuple[bool,str]:
# 自动合成指定数量的物品
# 会自动查找附近有无工作台，并直接进行合成
# 如果附近有工作台，会自动move前往工作台
# item是物品的名称
# count是物品的数量
# 返回值为tuple[bool,str]，bool为是否成功，str为可读文本结果

await bot.chat(message) -> bool:
# 发送中文聊天消息
# message是聊天消息（中文
# 返回值为bool，为是否成功

await bot.move(x,y,z) -> tuple[BlockPosition,float]:
# 移动到指定位置
# 会自动选择路径并移动，不需要手动放置或破坏方块，可以进行平地移动和垂直移动
# x,y,z是位置的坐标，必须输入x,y,z 三个参数
# 返回值为tuple[BlockPosition,float]，BlockPosition为最终到达位置，float为距离输入坐标的距离

await bot.view_container(x,y,z,type)
# 查看容器/方块内容（支持 chest / furnace / blast_furnace / smoker）
# 可以获得附近容器内的物品信息
# x,y,z: 方块坐标，type: 类型
# 返回：
# - chest: (ok: bool, items: List[Item], remaining_slots: int, text: str)
# - furnace: (ok: bool, input_item: Item|None, output_item: Item|None, fuel_item: Item|None, text: str)

await bot.use_chest(x,y,z,action,item,count) -> tuple[bool,List[Item],int]
# 对箱子进行存取操作
# action: "store" 或 "withdraw"
# item: 物品名称
# count: 物品数量
# 返回 (ok, items_after[List[Item]], remaining_slots[int])，items_after为箱子操作后的物品列表，remaining_slots为剩余空槽位数

await bot.use_furnace(x,y,z,action,item,count,slot) -> tuple[bool,Item|None,str]
# 放入或取出熔炼 输入槽 燃料 或 输出槽的物品
# action: "put" 或 "take"
# item=物品名称
# count=物品数量
# slot=槽位 input/fuel/output
# 返回 (ok, slot_item, text)，slot_item为操作后的槽的物品

await bot.set_location_point(name, info, position) -> tuple[bool,str]
# 设置坐标点，可以在后续的移动，采矿，使用方块等操作中使用
# name: 坐标点名称
# info: 坐标点信息，描述和简介
# position:BlockPosition 坐标点位置
# 返回值为tuple[bool,str]，bool为是否成功，str为可读文本结果

{retrieved_skills}

--------------------------------
请你根据以下信息做代码修改:
**环境信息**
{environment}

**物品信息**
{inventory_str}

**位置信息**
{position}

**周围方块的信息**
{nearby_block_info}

**最近游戏事件**
{event_str}

**玩家聊天记录**
{chat_str}

**坐标点信息**：
{location_list}
--------------------------------
上次执行的代码: 
```python code
{code_last_run}
```
输出结果：{output_last_run}
报错信息: {error_last_run}

上一次执行结果评估：{last_run_result}
原因：{adjust_reason}
调整建议：{suggestion}

**当前任务**
{task}

现在请你对代码进行修改，你应该按照以下标准回复我：

对结果的解释：你的计划中是否有遗漏的步骤？为什么代码没有完成任务？聊天记录和执行错误说明了什么问题？
Plan：请一步步说明如何在现在的情况下完成该任务。请特别关注背包（Inventory），因为它显示了你拥有的物品。也要关注附近的方块和你所处的位置，任务是否完成也取决于你最终的背包内容和周围方块的情况。
Code：
1）编写一个异步函数（async function），不要定义多余的函数，如果需要工具函数，可以在函数内定义。
2）尽可能复用上面提供的有用程序。
- 使用 'bot.mine_block(name, count)' 来收集方块。不要直接使用 'bot.dig'。
- 使用 'bot.craft_item(name, count)' 来合成物品。不要直接使用 'bot.craft'。
3）你的函数会被复用于更复杂的功能，因此应当通用且可复用。不要对背包内容做强假设（因为它可能会被后续更改），因此在使用物品前应始终检查是否拥有所需物品。如果没有，应先收集所需物品，并复用上述有用程序。
4）"上次执行的代码"部分的函数不会被保存或执行，不要复用那里列出的函数。
5）所有变量都应在函数内部定义，函数外定义的内容会被忽略。
6）记录执行的中间过程，并用print记录，以便后续对程序进行调试和调整。
7) 程序需要能够应对可能出现的意料外的情况，比如方块不存在，物品不存在，物品数量不足等。
8）不要写无限循环或递归函数。
9）不要使用 'bot.on' 或 'bot.once' 注册事件监听器，你绝对不需要它们。
10）为你的函数起一个有意义的名字（能体现任务内容）。
11）使用正确的 Python 语法并遵循 PEP 8 代码风格。
12）如有需要，在代码开头导入必要的模块。
13) 不要使用任何涉及系统的危险操作！！
------------------------------
你只能按照如下格式回复，请按照以下格式输出：
RESPONSE FORMAT:
Explain: ...
Plan:
1) ...
2) ...
3) ...
...

Code:
```python code
# main function
async def yourMainFunctionName(bot) {{
  # ...
}}
```
""",
            description="代码生成",
            parameters=["last_run_result","adjust_reason","suggestion","retrieved_skills","code_last_run","output_last_run","error_last_run","event_str","goal", "task", "environment", "thinking_list", "nearby_block_info", "position", "location_list", "chat_str", "inventory_str"],
        )
    )