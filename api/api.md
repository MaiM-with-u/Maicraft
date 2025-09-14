# MaicraftAgent Vue3 GUI 接口文档

## 概述

本文档为基于 MaicraftAgent 项目的 Vue3 GUI 提供了完整的接口规范。GUI 需要与运行中的 MaicraftAgent 后端服务进行通信，获取实时数据并执行控制操作。

## 技术栈要求

- **后端**: Python FastAPI + WebSocket
- **前端**: Vue3 + TypeScript
- **通信**: REST API + WebSocket (实时日志更新)

## 架构设计

### 服务启动方式

MaicraftAgent 需要扩展现有的 `main.py`，添加 Web 服务组件：

```python
# 在 main.py 中添加
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import websockets
import json
import asyncio
from datetime import datetime

app = FastAPI(title="MaicraftAgent GUI API", version="1.0.0")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境请限制域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局状态管理
class GlobalState:
    def __init__(self):
        self.connected_clients = set()
        self.last_log_timestamp = 0

global_state = GlobalState()
```

## 1. 日志查看功能 (Log Viewer)

**注意:** 当前系统使用 loguru 库进行日志记录，仅提供实时控制台输出，不支持历史日志存储和查询。

### 1.1 REST API 接口

#### 获取当前日志配置

```
GET /api/logs/config
```

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "level": "INFO"
  }
}
```

#### 获取日志级别

```
GET /api/logs/level
```

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "current_level": "INFO",
    "available_levels": ["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"]
  }
}
```

#### 更新日志级别

```
POST /api/logs/level
```

**请求体:**

```json
{
  "level": "DEBUG"
}
```

**响应:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "message": "日志级别已更新为 DEBUG"
  }
}
```

### 1.2 WebSocket 实时日志

#### 连接地址

```
ws://localhost:8000/ws/logs
```

#### 消息格式

**客户端发送:**

```json
{
  "type": "subscribe",
  "levels": ["INFO", "WARNING", "ERROR"],
  "modules": ["MCPClient", "MaiAgent"]
}
```

**服务端推送:**

```json
{
  "type": "log",
  "timestamp": 1704067200000,
  "level": "INFO",
  "module": "MCPClient",
  "message": "MCP 客户端已连接"
}
```

## 2. 配置管理功能 (Configuration)

### 2.1 获取配置

```
GET /api/config
```

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "inner": {
      "version": "0.2.0"
    },
    "bot": {
      "player_name": "EvilMai",
      "bot_name": "麦麦"
    },
    "game": {
      "goal": "以合适的步骤，建立营地，挖到16个钻石，并存储"
    },
    "llm": {
      "model": "qwen3-next-80b-a3b-instruct",
      "temperature": 0.2,
      "max_tokens": 1024,
      "api_key": "sk-***",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
    },
    "vlm": {
      "model": "Pro/THUDM/GLM-4.1V-9B-Thinking",
      "temperature": 0.3,
      "max_tokens": 1024,
      "enable": false
    },
    "logging": {
      "level": "INFO"
    }
  }
}
```

### 2.2 更新配置

```
POST /api/config/update
```

**请求体示例:**

```json
{
  "llm": {
    "temperature": 0.3,
    "max_tokens": 2048
  },
  "logging": {
    "level": "DEBUG"
  }
}
```

**响应:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "success": true,
    "message": "配置已更新",
    "restart_required": false
  }
}
```

### 2.3 重置配置

```
POST /api/config/reset
```

**响应:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "success": true,
    "message": "配置已重置为默认值"
  }
}
```

### 2.4 验证配置

```
POST /api/config/validate
```

**请求体:** 完整的配置对象

**响应:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "valid": true,
    "errors": [],
    "warnings": ["API密钥格式不正确"]
  }
}
```

## 3. 任务管理功能 (Task Management)

### 3.1 获取任务列表

```
GET /api/tasks
```

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "tasks": [
      {
        "id": "1",
        "details": "使用工作台合成石镐，需要3个cobblestone和2个stick",
        "done_criteria": "物品栏中拥有3个cobblestone和2个stick，并在工作台完成石镐合成",
        "progress": "尚未开始",
        "done": false
      }
    ],
    "total": 5,
    "completed": 2,
    "in_progress": 2,
    "pending": 1
  }
}
```

### 3.2 获取单个任务

```
GET /api/tasks/{task_id}
```

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "id": "1",
    "details": "使用工作台合成石镐，需要3个cobblestone和2个stick",
    "done_criteria": "物品栏中拥有3个cobblestone和2个stick，并在工作台完成石镐合成",
    "progress": "尚未开始",
    "done": false
  }
}
```

### 3.3 创建任务

```
POST /api/tasks
```

**请求体:**

```json
{
  "details": "建立营地",
  "done_criteria": "建造了基础庇护所和工作台"
}
```

**响应:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "id": "2",
    "details": "建立营地",
    "done_criteria": "建造了基础庇护所和工作台",
    "progress": "尚未开始",
    "done": false
  }
}
```

### 3.4 更新任务

```
POST /api/tasks/{task_id}/update
```

**请求体:**

```json
{
  "progress": "已建造工作台，正在收集木材",
  "done": false
}
```

**响应:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "success": true,
    "message": "任务已更新"
  }
}
```

### 3.5 删除任务

```
POST /api/tasks/{task_id}/delete
```

**响应:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "success": true,
    "message": "任务已删除"
  }
}
```

### 3.6 标记任务完成

```
POST /api/tasks/{task_id}/complete
```

**响应:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "success": true,
    "message": "任务已标记为完成"
  }
}
```

### 3.7 批量操作

```
POST /api/tasks/batch
```

**请求体:**

```json
{
  "operation": "delete_completed",
  "task_ids": ["1", "2", "3"]
}
```

**响应:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "success": true,
    "message": "批量操作完成",
    "affected_count": 2
  }
}
```

**注意:** 当前系统只支持 `delete_completed` 操作，即删除已完成的任务。系统会自动维护任务数量不超过5个。

## 4. 事件查询功能 (Event Query)

### 4.1 获取事件列表

```
GET /api/events?type=all&limit=50&start_time=1704067200000
```

**参数说明:**

- `type`: 事件类型 (all, thinking, action, event, notice)
- `limit`: 返回条数 (默认: 50)
- `start_time`: 开始时间 (13位数字时间戳)

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "events": [
      {
        "content": "生命值和饥饿值均为0，必须先恢复生存状态...",
        "type": "thinking",
        "timestamp": 1757810821.6623514
      },
      {
        "content": "执行动作 1/1：{'error': {'code': 'AllocationQuota.FreeTierOnly'...",
        "type": "action",
        "timestamp": 1757810758.021458
      },
      {
        "content": "玩家EvilMai收集了 1 个 Diorite",
        "type": "event",
        "timestamp": 1757810830.2863913
      }
    ],
    "total": 20,
    "has_more": false
  }
}
```

### 4.2 获取事件统计

```
GET /api/events/stats?period=1h
```

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "period": "1h",
    "stats": {
      "thinking": 8,
      "action": 3,
      "event": 9,
      "total": 20
    },
    "recent_events": [
      { "type": "thinking", "count": 8 },
      { "type": "event", "count": 9 },
      { "type": "action", "count": 3 }
    ]
  }
}
```

### 4.3 搜索事件

```
GET /api/events/search?keyword=钻石&type=action&limit=20
```

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "events": [
      {
        "content": "玩家EvilMai收集了 1 个 Diorite",
        "type": "event",
        "timestamp": 1757810830.2863913
      }
    ],
    "total": 3,
    "has_more": false
  }
}
```

## 5. MCP 工具管理功能 (MCP Tools)

### 5.1 获取工具列表

```
GET /api/mcp/tools
```

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "tools": [
      {
        "name": "move",
        "description": "移动到指定位置",
        "parameters": {
          "type": "object",
          "properties": {
            "x": { "type": "number", "description": "X坐标" },
            "y": { "type": "number", "description": "Y坐标" },
            "z": { "type": "number", "description": "Z坐标" }
          },
          "required": ["x", "y", "z"]
        },
        "category": "movement",
        "enabled": true
      },
      {
        "name": "mine_block",
        "description": "挖掘指定方块",
        "parameters": {
          "type": "object",
          "properties": {
            "x": { "type": "number" },
            "y": { "type": "number" },
            "z": { "type": "number" },
            "face": { "type": "string", "enum": ["north", "south", "east", "west", "up", "down"] }
          },
          "required": ["x", "y", "z"]
        },
        "category": "mining",
        "enabled": true
      }
    ],
    "categories": ["movement", "mining", "crafting", "combat"],
    "total": 25
  }
}
```

### 5.2 获取工具详情

```
GET /api/mcp/tools/{tool_name}
```

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "name": "move",
    "description": "移动到指定位置",
    "parameters": {
      "type": "object",
      "properties": {
        "x": { "type": "number", "description": "X坐标" },
        "y": { "type": "number", "description": "Y坐标" },
        "z": { "type": "number", "description": "Z坐标" }
      },
      "required": ["x", "y", "z"]
    },
    "category": "movement",
    "enabled": true
  }
}
```

### 5.3 调用工具

```
POST /api/mcp/tools/{tool_name}/call
```

**请求体:**

```json
{
  "parameters": {
    "x": 100,
    "y": 64,
    "z": 200
  },
  "async": false,
  "timeout": 30
}
```

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "call_id": "call_001",
    "status": "success",
    "result": {
      "content": [
        {
          "type": "text",
          "text": "成功移动到位置 (100, 64, 200)"
        }
      ],
      "is_error": false,
      "execution_time": 2.5
    }
  }
}
```

### 5.4 获取调用历史

```
GET /api/mcp/tools/calls?limit=20&tool_name=move&status=success
```

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "calls": [
      {
        "call_id": "call_001",
        "tool_name": "move",
        "parameters": { "x": 100, "y": 64, "z": 200 },
        "status": "success",
        "timestamp": 1704067200000,
        "execution_time": 2.5,
        "result": {
          "content": "成功移动到位置",
          "is_error": false
        }
      }
    ],
    "total": 45
  }
}
```

### 5.5 批量工具调用

```
POST /api/mcp/tools/batch
```

**请求体:**

```json
{
  "calls": [
    {
      "tool_name": "move",
      "parameters": { "x": 100, "y": 64, "z": 200 }
    },
    {
      "tool_name": "mine_block",
      "parameters": { "x": 101, "y": 64, "z": 200 }
    }
  ],
  "sequential": true
}
```

**响应:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "batch_id": "batch_001",
    "results": [
      {
        "call_id": "call_001",
        "tool_name": "move",
        "status": "success",
        "result": {
          "content": "成功移动到位置",
          "is_error": false,
          "execution_time": 2.5
        }
      },
      {
        "call_id": "call_002",
        "tool_name": "mine_block",
        "status": "success",
        "result": {
          "content": "成功挖掘方块",
          "is_error": false,
          "execution_time": 1.8
        }
      }
    ],
    "total_calls": 2,
    "successful_calls": 2,
    "failed_calls": 0
  }
}
```

## 6. 系统状态监控 (System Status)

**注意:** 当前系统提供基础的状态监控功能，主要包括版本信息、连接状态等基本信息。完整的系统资源监控（如CPU、内存）需要在后续版本中实现。

### 6.1 获取系统状态

```
GET /api/system/status
```

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "status": "running",
    "version": "0.2.0",
    "mcp_connection": {
      "status": "connected",
      "server": "ChangingSelf.xyz:50226",
      "username": "EvilMai"
    },
    "active_tasks": 1,
    "start_time": 1704067200000
  }
}
```

### 6.2 获取系统信息

```
GET /api/system/info
```

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "version": "0.2.0",
    "python_version": "3.9.0",
    "platform": "Windows",
    "config_path": "E:\\01_Projects\\Code\\AI\\Minecraft\\MaicraftAgent\\config.toml",
    "data_directory": "E:\\01_Projects\\Code\\AI\\Minecraft\\MaicraftAgent\\data",
    "logs_directory": "E:\\01_Projects\\Code\\AI\\Minecraft\\MaicraftAgent\\logs"
  }
}
```

### 6.3 获取连接状态

```
GET /api/system/connections
```

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "mcp_server": {
      "connected": true,
      "host": "ChangingSelf.xyz",
      "port": 50226,
      "username": "EvilMai",
      "connection_time": 1704067200000
    },
    "websocket_clients": 0,
    "last_heartbeat": 1704069000000
  }
}
```

## 7. WebSocket 通用规范

### 7.1 连接管理

**连接建立:**

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/general')

ws.onopen = () => {
  console.log('WebSocket connected')
}

ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  handleMessage(data)
}

ws.onclose = () => {
  console.log('WebSocket disconnected')
}
```

**心跳机制:**

```json
// 客户端发送
{
  "type": "ping",
  "timestamp": 1704067200000
}

// 服务端回复
{
  "type": "pong",
  "timestamp": 1704067200000
}
```

### 7.2 订阅机制

**订阅特定类型的数据:**

```json
{
  "type": "subscribe",
  "channels": ["logs", "tasks", "events", "system"],
  "filters": {
    "logs": {
      "levels": ["INFO", "WARNING", "ERROR"],
      "modules": ["MCPClient", "MaiAgent"]
    },
    "events": {
      "types": ["thinking", "action"]
    }
  }
}
```

**取消订阅:**

```json
{
  "type": "unsubscribe",
  "channels": ["logs"]
}
```

## 8. 错误处理规范

### 8.1 HTTP 错误响应

```json
{
  "isSuccess": false,
  "message": "VALIDATION_ERROR: 输入参数无效",
  "data": {
    "details": {
      "field": "temperature",
      "reason": "必须在 0.0-2.0 之间"
    }
  },
  "timestamp": 1704067200000,
  "request_id": "req_001"
}
```

### 8.2 WebSocket 错误消息

```json
{
  "type": "error",
  "errorCode": "CONNECTION_FAILED",
  "message": "无法连接到 MCP 服务器",
  "timestamp": 1704067200000
}
```

### 8.3 错误代码定义

| 错误代码              | 说明             |
| --------------------- | ---------------- |
| `VALIDATION_ERROR`    | 输入参数验证失败 |
| `RESOURCE_NOT_FOUND`  | 请求的资源不存在 |
| `PERMISSION_DENIED`   | 权限不足         |
| `RATE_LIMIT_EXCEEDED` | 请求频率超限     |
| `INTERNAL_ERROR`      | 服务器内部错误   |
| `CONNECTION_FAILED`   | 连接失败         |
| `TIMEOUT_ERROR`       | 请求超时         |

## 9. 安全考虑

### 9.1 API 密钥管理

- 使用环境变量存储敏感信息
- API 响应中隐藏敏感字段
- 支持密钥轮换

### 9.2 请求限制

- 实现速率限制防止滥用
- 对批量操作设置合理的限制
- 监控异常请求模式

### 9.3 CORS 配置

```python
# 生产环境建议的 CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-gui-domain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

## 10. 部署和配置

### 10.1 环境变量

```bash
# 服务器配置
GUI_API_HOST=0.0.0.0
GUI_API_PORT=8000

# 安全配置
GUI_API_SECRET_KEY=your-secret-key-here
GUI_ALLOWED_ORIGINS=https://your-gui-domain.com,http://localhost:3000

# 数据库配置 (如果需要)
GUI_DATABASE_URL=sqlite:///./gui.db

# 日志配置
GUI_LOG_LEVEL=INFO
GUI_LOG_MAX_SIZE=10MB
GUI_LOG_RETENTION=7
```

### 10.2 Docker 部署

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 10.3 启动命令

```bash
# 开发环境
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 生产环境
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 11. 测试和调试

### 11.1 API 测试工具

推荐使用以下工具进行 API 测试：

- **Postman**: REST API 测试
- **WebSocket King**: WebSocket 测试
- **curl**: 命令行测试

### 11.2 示例测试脚本

```bash
# 测试日志 API
curl http://localhost:8000/api/logs/history?limit=10

# 测试任务 API
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"details": "测试任务", "done_criteria": "任务完成"}'

# 测试 MCP 工具
curl http://localhost:8000/api/mcp/tools
```

## 12. 更新日志

### v1.0.0 (2024-01-01)

- 初始版本发布
- 支持日志查看、配置管理、任务管理、事件查询、MCP 工具调用
- WebSocket 实时数据推送
- 完整的错误处理和安全机制

---

## 接口对齐检查结果

### ✅ 已对齐的功能模块

#### 1. **任务管理功能** ⭐⭐⭐⭐⭐

- **完全匹配**: 数据结构、方法、限制条件都与实际代码一致
- **核心功能**: 增删改查、状态管理、智能清理机制
- **数据存储**: JSON格式，完全匹配实际实现

#### 2. **配置管理功能** ⭐⭐⭐⭐⭐

- **完全匹配**: Pydantic模型结构与文档描述一致
- **支持功能**: 读取、更新、验证、重置配置
- **文件格式**: TOML格式配置，支持版本更新

#### 3. **事件查询功能** ⭐⭐⭐⭐⭐

- **完全匹配**: 数据格式 `[content, type, timestamp]` 与实际存储一致
- **支持类型**: thinking, action, event, notice
- **存储机制**: JSON文件持久化，自动限制数量

#### 4. **MCP工具管理功能** ⭐⭐⭐⭐⭐

- **完全匹配**: FastMCP客户端集成，支持工具调用
- **连接配置**: JSON格式服务器配置
- **调用机制**: 异步调用，支持参数传递

### ⚠️ 需要后端实现的接口

#### 1. **日志查看功能** (部分实现)

- **当前状态**: 仅实时输出，无历史存储
- **建议实现**: 添加日志文件存储和查询功能
- **影响**: 前端只能查看实时日志，无法历史回溯

#### 2. **系统状态监控** (基础实现)

- **当前状态**: 基础信息可用，无资源监控
- **建议实现**: 添加CPU、内存、性能指标监控
- **影响**: 前端只能获取基础状态信息

### 🔧 技术架构说明

#### 数据存储层

```python
# 任务系统 - JSON文件存储
mai_to_do_list = ToDoList()  # data/todo_list.json

# 思考日志 - JSON文件存储
global_thinking_log = ThinkingLog()  # data/thinking_log.json

# 配置系统 - TOML文件存储
global_config = load_config_from_dict(config_dict)  # config.toml
```

#### 核心组件关系

```
MaicraftAgent
├── ToDoList (任务管理)
├── ThinkingLog (事件记录)
├── MCPClient (工具调用)
├── Configuration (配置管理)
└── Logger (实时日志)
```

#### 数据流向

```
用户操作 → Web API → 业务逻辑 → 数据持久化
    ↓
Vue3前端 ← REST/WS ← 后端服务 ← JSON/TOML文件
```

本文档将根据项目发展持续更新。如有疑问，请参考具体的 API 实现代码或联系开发团队。
