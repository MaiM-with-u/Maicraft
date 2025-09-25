# MaicraftAgent API

## 快速开始

```bash
# 启动API服务器
python -c "from api import start_api_server; import asyncio; asyncio.run(start_api_server())"
```

## 响应格式

**成功响应:**
```json
{
  "code": "SUCCESS",
  "success": true,
  "message": "操作成功",
  "data": {...},
  "timestamp": 1704067200000
}
```

**错误响应:**
```json
{
  "code": "ERROR",
  "success": false,
  "message": "操作失败",
  "error_code": "ERROR_CODE",
  "data": null,
  "timestamp": 1704067200000
}
```

**警告响应:**
```json
{
  "code": "WARNING",
  "success": true,
  "message": "警告信息",
  "data": {...},
  "timestamp": 1704067200000
}
```

**错误码:** `INTERNAL_ERROR`, `VALIDATION_ERROR`, `RESOURCE_NOT_FOUND`, `INVALID_PARAMETER`, `OPERATION_FAILED`, `CONNECTION_ERROR`, `SUBSCRIPTION_ERROR`, `GAME_STATE_ERROR`, `ENVIRONMENT_ERROR`

## 1. 健康检查

```
GET /health
```

**响应:** `{"status": "healthy", "service": "MaicraftAgent API", "version": "1.0.0"}`

## 2. 日志管理

### REST API

| 方法 | 端点 | 说明 | 返回数据结构 |
|------|------|------|-------------|
| GET | `/api/logs/config` | 获取日志配置 | `{level: string}` |
| GET | `/api/logs/level` | 获取日志级别信息 | `{current_level: string, available_levels: string[]}` |
| POST | `/api/logs/level` | 更新日志级别 | `{message: string}` |
| GET | `/api/logs/recent` | 获取最近日志 | `{logs: LogEntry[], total: number, has_more: boolean}` |
| GET | `/api/logs/stats` | 获取日志统计 | `{total_logs: number, level_counts: object, module_counts: object}` |
| POST | `/api/logs/clear` | 清空日志缓存 | `{cleared_count: number, message: string}` |

**LogEntry结构:**
```json
{
  "timestamp": 1704067200000,
  "level": "INFO",
  "module": "MCPClient",
  "message": "日志消息",
  "file": "client.py",
  "line": 45
}
```

**查询参数 (recent):**
- `limit`: 返回条数 (默认100)
- `level`: 过滤级别
- `module`: 过滤模块
- `message_contains`: 消息过滤
- `since_minutes`: 时间范围

**更新级别请求:**
```json
{"level": "DEBUG"}
```

### WebSocket 实时日志

```
WebSocket: /ws/logs
```

**订阅消息:**
```json
{"type": "subscribe", "levels": ["INFO", "WARNING"], "modules": ["MCPClient"]}
```

**推送消息:**
```json
{
  "type": "log",
  "timestamp": 1704067200000,
  "level": "INFO",
  "module": "MCPClient",
  "message": "MCP客户端已连接",
  "file": "client.py",
  "line": 45
}
```

#### 心跳机制

**客户端发送:** `{"type": "ping", "timestamp": 1704067200000}`  
**服务端回复:** `{"type": "pong", "timestamp": 1704067200000}`

## 3. 游戏状态管理

### REST API

| 方法 | 端点 | 说明 | 返回数据结构 |
|------|------|------|-------------|
| GET | `/api/environment/snapshot` | 获取环境快照 | `{player: Player, world: World, markers: Marker[], timestamp: number}` |
| GET | `/api/environment/player` | 获取玩家信息 | `Player` |
| GET | `/api/environment/inventory` | 获取物品栏 | `{occupied_slots: number, total_slots: number, items: InventoryItem[]}` |
| GET | `/api/environment/world` | 获取世界信息 | `World` |
| GET | `/api/environment/nearby/entities` | 获取附近实体 | `{entities: Entity[], count: number, range: number}` |

**Player结构:**
```json
{
  "name": "EvilMai",
  "health": 20,
  "max_health": 20,
  "food": 18,
  "max_food": 20,
  "position": {"x": 123.5, "y": 64.0, "z": -456.8, "yaw": 45.2, "pitch": -12.3},
  "gamemode": "survival",
  "equipment": {"main_hand": {"name": "diamond_pickaxe", "count": 1, "damage": 5, "max_durability": 1561}}
}
```

**World结构:**
```json
{
  "time": {"time_of_day": 120914, "formatted_time": "夜晚", "day_count": 0},
  "weather": {"weather": "clear", "formatted_weather": "晴朗", "duration": 0},
  "location": {"dimension": "overworld", "biome": "plains", "light_level": 15}
}
```

**Entity结构:**
```json
{
  "name": "cow",
  "display_name": "牛",
  "type": "animal",
  "distance": 12.5,
  "position": {"x": 130.5, "y": 64.0, "z": -450.2},
  "health": 10,
  "max_health": 10
}
```

**查询参数 (nearby/entities):**
- `range_limit`: 搜索范围 (默认16, 1-64)

### WebSocket 游戏状态

| 端点 | 说明 | 推送消息类型 |
|------|------|-------------|
| `/ws/game/player` | 玩家数据推送 | `player_update` |
| `/ws/game/world` | 世界数据推送 | `world_update` |
| `/ws/game/marker` | 标记点数据推送 | `marker_update` |

**订阅消息:**
```json
{"type": "subscribe", "update_interval": 1000}
```

**推送消息格式:**
```json
{
  "type": "player_update",  // 或 world_update, marker_update
  "timestamp": 1704067200000,
  "data": Player  // 根据端点类型使用相应数据结构
}
```

## 4. 位置管理

### REST API

| 方法 | 端点 | 说明 | 返回数据结构 |
|------|------|------|-------------|
| GET | `/api/locations` | 获取所有位置点 | `{locations: Location[], total: number}` |
| GET | `/api/locations/stats` | 获取位置统计 | `{total_locations: number, type_distribution: object}` |
| POST | `/api/locations` | 创建位置点 | `Location` |
| GET | `/api/locations/{name}` | 获取指定位置 | `Location` |
| PUT | `/api/locations/{name}` | 更新位置点 | `Location` |
| DELETE | `/api/locations/{name}` | 删除位置点 | `Location` |

**Location结构:**
```json
{
  "name": "camp",
  "info": "初始营地",
  "position": {"x": 11, "y": 65, "z": 8},
  "created_time": null,
  "visit_count": 0
}
```

**创建位置请求:**
```json
{"name": "camp", "info": "初始营地", "position": {"x": 11, "y": 65, "z": 8}}
```

## 5. 容器管理

### REST API

| 方法 | 端点 | 说明 | 返回数据结构 |
|------|------|------|-------------|
| GET | `/api/containers` | 获取容器列表 | `{containers: Container[], total: number, center_position: Position, range: number}` |
| GET | `/api/containers/verify/{x}/{y}/{z}` | 验证容器 | `{exists: boolean, position: Position, type: string, inventory: object}` |
| DELETE | `/api/containers/invalid` | 清理无效容器 | `{removed_count: number, message: string}` |
| GET | `/api/containers/stats` | 获取容器统计 | `{total_containers: number, chest_count: number, furnace_count: number}` |

**Container结构:**
```json
{
  "position": {"x": 100, "y": 64, "z": 200},
  "type": "chest",
  "inventory": {"0": 5, "1": 10},
  "verified": true
}
```

## 6. 方块管理

### REST API

| 方法 | 端点 | 说明 | 返回数据结构 |
|------|------|------|-------------|
| GET | `/api/blocks/stats` | 获取方块统计 | `{total_blocks: number, cached_blocks: number, memory_usage_mb: number}` |
| GET | `/api/blocks/region` | 获取区域方块 | `{blocks: Block[], total: number, center: Position2D, radius: number}` |
| GET | `/api/blocks/search` | 搜索方块 | `{blocks: Block[], total: number, search_term: string}` |
| GET | `/api/blocks/types` | 获取方块类型 | `{types: BlockType[], total_types: number}` |
| GET | `/api/blocks/position/{x}/{y}/{z}` | 获取位置方块 | `Block & {exists: boolean}` |
| DELETE | `/api/blocks/cache` | 清空缓存 | `{cleared_blocks: number, message: string}` |

**Block结构:**
```json
{
  "position": {"x": 100, "y": 64, "z": 200},
  "type": "stone",
  "name": "石头",
  "last_updated": "2024-01-01T12:00:00Z",
  "update_count": 5,
  "distance": 0.0
}
```

**BlockType结构:**
```json
{
  "type": "stone",
  "count": 500,
  "names": ["石头"]
}
```

## 7. 任务管理

### WebSocket 任务管理

```
WebSocket: /ws/tasks
```

#### 订阅任务更新

**订阅消息:**
```json
{
  "type": "subscribe",
  "update_interval": 5000
}
```

**订阅确认:**
```json
{
  "type": "subscribed",
  "message": "已订阅任务数据更新",
  "subscription": {
    "type": "tasks",
    "update_interval": 5000
  },
  "timestamp": 1704067200000
}
```

**注意:** `update_interval` 参数保留以保持向后兼容性，但现在任务更新是事件驱动的，只有在任务发生变化时才会推送更新。

#### 获取任务列表

**请求消息:**
```json
{
  "type": "get_tasks"
}
```

**响应消息:**
```json
{
  "type": "tasks_list",
  "message": "任务列表获取成功",
  "data": {
    "tasks": [
      {
        "id": "1",
        "details": "采集木材",
        "done_criteria": "收集到10个原木",
        "progress": "已收集5个原木",
        "done": false
      }
    ],
    "total": 1,
    "completed": 0,
    "pending": 1,
    "goal": "生存挑战",
    "is_done": false
  },
  "timestamp": 1704067200000
}
```

#### 添加任务

**请求消息:**
```json
{
  "type": "add_task",
  "details": "采集木材",
  "done_criteria": "收集到10个原木"
}
```

**响应消息:**
```json
{
  "type": "task_added",
  "message": "任务添加成功",
  "data": {
    "task_id": "1",
    "details": "采集木材",
    "done_criteria": "收集到10个原木",
    "progress": "尚未开始",
    "done": false
  },
  "timestamp": 1704067200000
}
```

#### 更新任务进度

**请求消息:**
```json
{
  "type": "update_task",
  "task_id": "1",
  "progress": "已收集5个原木"
}
```

**响应消息:**
```json
{
  "type": "task_updated",
  "message": "任务更新成功",
  "data": {
    "task_id": "1",
    "progress": "已收集5个原木"
  },
  "timestamp": 1704067200000
}
```

#### 删除任务

**请求消息:**
```json
{
  "type": "delete_task",
  "task_id": "1"
}
```

**响应消息:**
```json
{
  "type": "task_deleted",
  "message": "任务删除成功",
  "data": {
    "task_id": "1"
  },
  "timestamp": 1704067200000
}
```

#### 标记任务完成

**请求消息:**
```json
{
  "type": "mark_done",
  "task_id": "1"
}
```

**响应消息:**
```json
{
  "type": "task_marked_done",
  "message": "任务标记完成成功",
  "data": {
    "task_id": "1"
  },
  "timestamp": 1704067200000
}
```

#### 任务变更推送

当任务发生变化时（添加、更新、删除、标记完成），系统会自动推送更新给所有订阅的客户端（发起操作的客户端除外，避免重复推送）。

**推送消息:**
```json
{
  "type": "tasks_update",
  "timestamp": 1704067200000,
  "data": {
    "tasks": [
      {
        "id": "1",
        "details": "采集木材",
        "done_criteria": "收集到10个原木",
        "progress": "已收集10个原木",
        "done": true
      }
    ],
    "total": 1,
    "completed": 1,
    "pending": 0,
    "goal": "生存挑战",
    "is_done": true
  }
}
```

**推送触发条件:**
- 添加新任务时推送
- 更新任务进度时推送
- 删除任务时推送
- 标记任务完成时推送

#### 取消订阅

**请求消息:**
```json
{
  "type": "unsubscribe"
}
```

**响应消息:**
```json
{
  "type": "unsubscribed",
  "message": "已取消订阅任务数据",
  "timestamp": 1704067200000
}
```

**说明:** 任务更新现在是事件驱动的，不再依赖定期推送机制。

## 8. Token使用量监控

```
WebSocket: /ws/token-usage
```

**订阅消息:**
```json
{"type": "subscribe", "update_interval": 0, "model_filter": null}
```

**推送消息:**
```json
{
  "type": "token_usage_update",
  "timestamp": 1704067200000,
  "data": {
    "model_name": "qwen3-next-80b-a3b-instruct",
    "usage": {
      "model_name": "qwen3-next-80b-a3b-instruct",
      "total_prompt_tokens": 7643119,
      "total_completion_tokens": 572218,
      "total_tokens": 8215337,
      "total_calls": 2300,
      "total_cost": 9.910613,
      "first_call_time": 1757772240.156,
      "last_call_time": 1758332630.438,
      "last_updated": 1758332630.438
    },
    "summary": {
      "total_cost": 15.432,
      "total_prompt_tokens": 10000000,
      "total_completion_tokens": 2000000,
      "total_tokens": 12000000,
      "total_calls": 5000,
      "model_count": 3
    }
  }
}
```

**TokenUsage结构:**
```json
{
  "model_name": "string",
  "total_prompt_tokens": 0,
  "total_completion_tokens": 0,
  "total_tokens": 0,
  "total_calls": 0,
  "total_cost": 0.0,
  "first_call_time": 1704067200.000,
  "last_call_time": 1704067200.000,
  "last_updated": 1704067200.000
}
```

## 9. MCP工具

### REST API

| 方法 | 端点 | 说明 | 返回数据结构 |
|------|------|------|-------------|
| GET | `/api/mcp/tools` | 获取可用工具 | `{tools: Tool[], total: number}` |
| POST | `/api/mcp/tools/call` | 调用工具 | `{tool_name: string, arguments: object, result: CallToolResult}` |

**说明:** API直接返回MCP客户端的原始数据结构，不做额外处理。

**Tool结构 (MCP原始格式):**
```json
{
  "name": "tool_name",
  "description": "工具描述",
  "inputSchema": {
    "type": "object",
    "properties": {...},
    "required": [...]
  }
}
```

**工具调用请求:**
```json
{
  "tool_name": "tool_name",
  "arguments": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

**CallToolResult结构 (MCP原始格式):**
```json
{
  "content": [
    {
      "type": "text",
      "text": "执行结果文本"
    }
  ],
  "structured_content": null,
  "is_error": false,
  "data": {
    "custom_data": "value"
  }
}
```

**注意:**
- `content` 字段包含TextContent对象列表，每个对象都有 `type` 和 `text` 属性
- `structured_content` 字段可能为null或包含结构化数据
- `is_error` 表示工具调用是否出错
- `data` 字段包含工具返回的自定义数据

---

## 通用类型定义

**Position:** `{"x": number, "y": number, "z": number}`
**Position2D:** `{"x": number, "z": number}`
**InventoryItem:** `{"slot": number, "name": string, "display_name": string, "count": number, "damage": number, "max_durability": number}`

## WebSocket 错误处理

**错误消息格式:**
```json
{
  "type": "error",
  "errorCode": "ERROR_CODE",
  "message": "错误描述",
  "timestamp": 1704067200000
}
```

**常见WebSocket错误码:**
- `INVALID_INTERVAL`: 无效的更新间隔
- `UNKNOWN_MESSAGE_TYPE`: 未知消息类型
- `INVALID_JSON`: 无效的JSON格式
- `MESSAGE_PROCESSING_ERROR`: 消息处理失败
- `CONNECTION_ERROR`: 连接错误
- `SUBSCRIPTION_ERROR`: 订阅错误

**注意:** 所有WebSocket端点都支持双向心跳机制，客户端应每30秒发送ping消息。
