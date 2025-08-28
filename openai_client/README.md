# LLM客户端使用说明

这是一个精简的LLM调用客户端，基于OpenAI官方包实现，支持异步运行。

## 功能特性

- ✅ 异步LLM调用
- ✅ 支持工具调用（Function Calling）
- ✅ 自动从配置文件读取API密钥和基础URL
- ✅ 错误处理和日志记录
- ✅ 支持自定义温度和最大token数
- ✅ 精简的API设计

## 快速开始

### 1. 基本使用

```python
import asyncio
from llm_request import LLMClient

async def main():
    # 创建客户端（自动使用配置文件中的设置）
    client = LLMClient()
    
    # 简单聊天
    response = await client.simple_chat("你好，请介绍一下自己")
    print(response)

# 运行
asyncio.run(main())
```

### 2. 带工具的调用

```python
async def tool_example():
    client = LLMClient()
    
    # 定义工具
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "获取天气信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "城市名称"}
                    },
                    "required": ["location"]
                }
            }
        }
    ]
    
    # 调用工具
    result = await client.call_tool(
        "北京今天天气怎么样？",
        tools=tools,
        system_message="你是一个有用的助手，可以使用工具来帮助用户。"
    )
    
    print(result)
```

### 3. 自定义配置

```python
from llm_request import create_llm_client

async def custom_config():
    # 自定义配置
    config_data = {
        "llm": {
            "model": "gpt-4o-mini",
            "temperature": 0.1,
            "api_key": "your-api-key",
            "base_url": "https://api.openai.com/v1"
        }
    }
    
    client = await create_llm_client(config_data)
    response = await client.simple_chat("测试消息")
    print(response)
```

## API参考

### LLMClient类

#### 构造函数
```python
LLMClient(config: Optional[MaicraftConfig] = None)
```

#### 主要方法

##### chat_completion()
```python
async def chat_completion(
    self,
    prompt: str,
    tools: Optional[List[Dict[str, Any]]] = None,
    system_message: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> Dict[str, Any]
```

完整的聊天完成调用，返回详细结果。

##### simple_chat()
```python
async def simple_chat(
    self,
    prompt: str,
    system_message: Optional[str] = None
) -> str
```

简化的聊天接口，只返回文本内容。

##### call_tool()
```python
async def call_tool(
    self,
    prompt: str,
    tools: List[Dict[str, Any]],
    system_message: Optional[str] = None
) -> Dict[str, Any]
```

专门用于工具调用的接口。

##### get_config_info()
```python
def get_config_info(self) -> Dict[str, Any]
```

获取当前配置信息。

### 便捷函数

##### create_llm_client()
```python
async def create_llm_client(
    config_data: Optional[Dict[str, Any]] = None
) -> LLMClient
```

创建LLM客户端的便捷函数。

## 配置说明

客户端会自动从以下位置读取配置：

1. `config.toml` 文件中的 `[llm]` 部分
2. 环境变量（如果配置文件中未设置）
3. 默认配置值

### 配置字段

- `model`: LLM模型名称
- `api_key`: API密钥
- `base_url`: API基础URL
- `temperature`: 温度参数（0.0-2.0）
- `max_token_limit`: 最大token限制

## 错误处理

客户端内置了完善的错误处理机制：

- API调用失败时返回错误信息
- 网络异常自动重试
- 详细的日志记录
- 优雅的错误响应格式

## 测试

运行测试文件：

```bash
cd src/plugins/maicraft/openai_client
python test_llm.py
```

## 依赖要求

- `openai` >= 1.0.0
- `pydantic` >= 2.0.0
- `asyncio` (Python 3.7+)

## 注意事项

1. 确保API密钥有效且有足够的配额
2. 网络连接稳定，建议在异步环境中使用
3. 工具调用需要按照OpenAI的格式定义
4. 建议在生产环境中设置适当的超时时间
