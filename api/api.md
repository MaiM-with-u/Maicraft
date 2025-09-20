# MaicraftAgent API 接口文档

## 全局响应格式

### 成功响应

```json
{
  "isSuccess": true,
  "message": "操作成功",
  "data": {
    // 具体数据内容
  },
  "timestamp": 1704067200000
}
```

### 错误响应

```json
{
  "isSuccess": false,
  "message": "错误描述",
  "data": null,
  "timestamp": 1704067200000
}
```

## 1. 健康检查

### 健康检查

````
GET /health
````

**响应示例:**

```json
{
  "status": "healthy",
  "service": "MaicraftAgent API",
  "version": "1.0.0"
}
```

## 2. 日志管理

基于日志服务实现，提供日志配置管理、实时日志推送等功能。

### 2.1 REST API 接口

#### 获取日志配置

````
GET /api/logs/config
````

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

#### 获取日志级别信息

````
GET /api/logs/level
````

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

````
POST /api/logs/level
````

**请求体:**

```json
{
  "level": "DEBUG"
}
```

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "message": "日志级别已更新为 DEBUG"
  }
}
```

#### 获取最近日志

````
GET /api/logs/recent?limit=100&level=INFO&module=MCPClient&message_contains=error&since_minutes=60
````

**查询参数:**
- `limit` (可选): 返回日志条数，默认100，最大200
- `level` (可选): 过滤日志级别
- `module` (可选): 过滤模块名称
- `message_contains` (可选): 消息包含的文本
- `since_minutes` (可选): 最近N分钟内的日志

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "logs": [
      {
        "timestamp": 1704067200000,
        "level": "INFO",
        "module": "MCPClient",
        "message": "MCP客户端已连接",
        "file": "client.py",
        "line": 45
      }
    ],
    "total": 50,
    "has_more": true
  }
}
```

#### 获取日志统计

````
GET /api/logs/stats
````

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "total_logs": 1250,
    "level_counts": {
      "INFO": 800,
      "WARNING": 200,
      "ERROR": 50
    },
    "module_counts": {
      "MCPClient": 300,
      "GameStateService": 450
    },
    "time_range": {
      "start": "2024-01-01T00:00:00Z",
      "end": "2024-01-01T12:00:00Z"
    },
    "max_capacity": 10000,
    "utilization_percent": 12.5
  }
}
```

#### 清空日志缓存

````
POST /api/logs/clear
````

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "success",
  "data": {
    "cleared_count": 1250,
    "message": "已清空 1250 条日志记录"
  }
}
```

### 2.2 WebSocket 实时日志

#### 连接地址

````
ws://localhost:20914/ws/logs
````

#### 订阅消息

**客户端发送:**

```json
{
  "type": "subscribe",
  "levels": ["INFO", "WARNING", "ERROR"],
  "modules": ["MCPClient", "GameStateService"]
}
```

#### 推送消息

**服务端推送:**

```json
{
  "type": "log",
  "timestamp": 1704067200000,
  "level": "INFO",
  "module": "MCPClient",
  "message": "MCP客户端已连接"
}
```

#### 心跳机制

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

## 3. 游戏状态管理

基于游戏状态服务实现，提供游戏环境数据的获取和管理。

### 3.1 REST API 接口

#### 获取环境快照

````
GET /api/environment/snapshot
````

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "获取环境快照成功",
  "data": {
    "player": {
      "name": "EvilMai",
      "health": 20,
      "max_health": 20,
      "position": {
        "x": 123.5,
        "y": 64.0,
        "z": -456.8
      }
    },
    "world": {
      "time": {
        "time_of_day": 120914,
        "formatted_time": "夜晚",
        "day_count": 0
      },
      "weather": {
        "weather": "clear",
        "formatted_weather": "晴朗"
      }
    },
    "markers": {
      "markers": []
    },
    "timestamp": 1704067200000
  }
}
```

#### 获取玩家信息

````
GET /api/environment/player
````

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "获取玩家信息成功",
  "data": {
    "name": "EvilMai",
    "health": 20,
    "max_health": 20,
    "food": 18,
    "max_food": 20,
    "experience": 1250,
    "level": 15,
    "position": {
      "x": 123.5,
      "y": 64.0,
      "z": -456.8,
      "yaw": 45.2,
      "pitch": -12.3,
      "on_ground": true
    },
    "gamemode": "survival",
    "equipment": {
      "main_hand": {
        "name": "diamond_pickaxe",
        "count": 1,
        "damage": 5
      }
    },
    "inventory": {
      "occupied_slots": 15,
      "total_slots": 36,
      "empty_slots": 21,
      "items": [
        {
          "slot": 0,
          "name": "diamond_pickaxe",
          "display_name": "钻石镐",
          "count": 1,
          "max_stack": 1,
          "damage": 5,
          "max_damage": 1561
        }
      ]
    }
  }
}
```

#### 获取物品栏信息

````
GET /api/environment/inventory
````

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "获取物品栏信息成功",
  "data": {
    "occupied_slots": 15,
    "total_slots": 36,
    "empty_slots": 21,
    "items": [
      {
        "slot": 0,
        "name": "diamond_pickaxe",
        "display_name": "钻石镐",
        "count": 1,
        "max_stack": 1,
        "damage": 5,
        "max_damage": 1561
      }
    ]
  }
}
```

#### 获取世界信息

````
GET /api/environment/world
````

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "获取世界信息成功",
  "data": {
    "time": {
      "time_of_day": 120914,
      "formatted_time": "夜晚",
      "day_count": 0
    },
    "weather": {
      "weather": "clear",
      "formatted_weather": "晴朗",
      "duration": 0
    },
    "location": {
      "dimension": "overworld",
      "biome": "plains",
      "light_level": 15
    },
    "nearby_blocks": [
      {
        "name": "grass_block",
        "position": {
          "x": 124,
          "y": 63,
          "z": -457
        },
        "distance": 2.1
      }
    ],
    "nearby_entities": [
      {
        "name": "cow",
        "display_name": "牛",
        "type": "animal",
        "distance": 12.5,
        "position": {
          "x": 130.5,
          "y": 64.0,
          "z": -450.2
        },
        "health": 10,
        "max_health": 10
      }
    ]
  }
}
```

#### 获取附近实体

````
GET /api/environment/nearby/entities?range_limit=16
````

**查询参数:**
- `range_limit` (可选): 搜索范围，默认16，范围1-64

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "获取附近实体成功",
  "data": {
    "entities": [
      {
        "name": "cow",
        "display_name": "牛",
        "type": "animal",
        "distance": 12.5,
        "position": {
          "x": 130.5,
          "y": 64.0,
          "z": -450.2
        },
        "health": 10,
        "max_health": 10
      }
    ],
    "count": 1,
    "range": 16
  }
}
```

### 3.2 WebSocket 实时游戏状态

系统提供三个专用WebSocket端点，实现实时数据推送。

#### 玩家数据端点

````
ws://localhost:20914/ws/game/player
````

**订阅消息:**
```json
{
  "type": "subscribe",
  "update_interval": 1000
}
```

**推送数据:**
```json
{
  "type": "player_update",
  "timestamp": 1704067200000,
  "data": {
    "name": "EvilMai",
    "health": 20,
    "max_health": 20,
    "position": {
      "x": 123.5,
      "y": 64.0,
      "z": -456.8
    }
  }
}
```

#### 世界数据端点

````
ws://localhost:20914/ws/game/world
````

**订阅消息:**
```json
{
  "type": "subscribe",
  "update_interval": 2000
}
```

**推送数据:**
```json
{
  "type": "world_update",
  "timestamp": 1704067200000,
  "data": {
    "time": {
      "time_of_day": 120914,
      "formatted_time": "夜晚"
    },
    "weather": {
      "weather": "clear",
      "formatted_weather": "晴朗"
    }
  }
}
```

#### 标记点数据端点

````
ws://localhost:20914/ws/game/marker
````

**订阅消息:**
```json
{
  "type": "subscribe",
  "update_interval": 0
}
```

**推送数据:**
```json
{
  "type": "marker_update",
  "timestamp": 1704067200000,
  "data": {
    "markers": []
  }
}
```

#### 心跳机制

为保持WebSocket连接稳定，所有WebSocket端点都使用双向心跳机制：

**客户端 → 服务端心跳:**
```json
{
  "type": "ping",
  "timestamp": 1704067200000
}
```

**服务端 → 客户端心跳:**
```json
{
  "type": "ping",
  "timestamp": 1704067200000,
  "message": "服务器保持连接ping"
}
```

**心跳响应:**
```json
{
  "type": "pong",
  "timestamp": 1704067200000
}
```

**心跳配置:**
- 客户端应每30秒发送一次ping
- 服务端在60秒无消息后发送ping
- 90秒无心跳响应断开连接
- 建议客户端定期（30秒）发送ping以保持连接

### 3.3 WebSocket Token使用量监控

系统提供Token使用量实时监控WebSocket端点，支持订阅Token使用量更新推送。

#### Token使用量端点

```
ws://localhost:20914/ws/token-usage
```

**订阅消息:**

```json
{
  "type": "subscribe",
  "update_interval": 0,
  "model_filter": "qwen"  // 可选：模型名称过滤器，支持模糊匹配
}
```

**参数说明:**
- `update_interval`: 更新间隔（毫秒），0表示实时推送（每次使用量更新时推送）
- `model_filter`: 可选的模型过滤器，只推送匹配的模型使用量

**推送数据:**

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
      "first_call_time": 1757772240.156091,
      "last_call_time": 1758332630.4386134,
      "last_updated": 1758332630.4386134
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

**数据说明:**
- `model_name`: 更新的模型名称
- `usage`: 该模型的详细使用量统计
- `summary`: 所有模型的总费用汇总

**获取当前使用量:**

```json
{
  "type": "get_usage",
  "model_name": "qwen3-next-80b-a3b-instruct"  // 可选：指定模型，不传则获取所有模型
}
```

## 4. 位置管理

基于位置点系统实现，提供位置点的增删改查功能。

#### 获取所有位置点

````
GET /api/locations
````

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "获取位置点列表成功",
  "data": {
    "locations": [
      {
        "name": "home",
        "info": "主基地",
        "position": {
          "x": 100.5,
          "y": 64.0,
          "z": 200.3
        },
        "created_time": null,
        "visit_count": 0
      }
    ],
    "total": 1
  }
}
```

#### 获取位置统计

````
GET /api/locations/stats
````

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "获取位置统计成功",
  "data": {
    "total_locations": 5,
    "type_distribution": {},
    "most_visited": null,
    "recently_added": null
  }
}
```

#### 添加位置点

````
POST /api/locations
````

**请求体:**

```json
{
  "name": "mine",
  "info": "矿洞入口",
  "position": {
    "x": 50.0,
    "y": 30.0,
    "z": 100.0
  }
}
```

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "添加位置点成功",
  "data": {
    "name": "mine",
    "info": "矿洞入口",
    "position": {
      "x": 50.0,
      "y": 30.0,
      "z": 100.0
    }
  }
}
```

#### 获取指定位置点

````
GET /api/locations/{name}
````

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "获取位置点成功",
  "data": {
    "name": "home",
    "info": "主基地",
    "position": {
      "x": 100.5,
      "y": 64.0,
      "z": 200.3
    }
  }
}
```

#### 更新位置点

````
PUT /api/locations/{name}
````

**请求体:**

```json
{
  "info": "更新后的主基地信息"
}
```

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "更新位置点成功",
  "data": {
    "name": "home",
    "info": "更新后的主基地信息",
    "position": {
      "x": 100.5,
      "y": 64.0,
      "z": 200.3
    }
  }
}
```

#### 删除位置点

````
DELETE /api/locations/{name}
````

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "删除位置点成功",
  "data": {
    "name": "mine",
    "info": "矿洞入口",
    "position": {
      "x": 50.0,
      "y": 30.0,
      "z": 100.0
    }
  }
}
```

## 5. 容器管理

基于容器缓存系统实现，提供容器查询和管理功能。

#### 获取容器列表

````
GET /api/containers?container_type=all&range_limit=32.0
````

**查询参数:**
- `container_type` (可选): 容器类型，all/chest/furnace，默认all
- `range_limit` (可选): 搜索范围，默认32.0，范围1.0-128.0

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "获取容器列表成功",
  "data": {
    "containers": [
      {
        "position": {
          "x": 100,
          "y": 64,
          "z": 200
        },
        "type": "chest",
        "inventory": {
          "0": 5,
          "1": 10
        },
        "verified": true
      }
    ],
    "total": 1,
    "center_position": {
      "x": 123.5,
      "y": 64.0,
      "z": -456.8
    },
    "range": 32.0,
    "type_filter": "all"
  }
}
```

#### 验证容器存在

````
GET /api/containers/verify/{x}/{y}/{z}
````

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "容器验证完成",
  "data": {
    "exists": true,
    "position": {
      "x": 100,
      "y": 64,
      "z": 200
    },
    "type": "chest",
    "verified": true,
    "inventory": {
      "0": 5,
      "1": 10
    }
  }
}
```

#### 清理无效容器

````
DELETE /api/containers/invalid
````

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "清理无效容器完成",
  "data": {
    "removed_count": 2,
    "message": "成功清理了 2 个不存在的容器"
  }
}
```

#### 获取容器统计

````
GET /api/containers/stats
````

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "获取容器统计成功",
  "data": {
    "total_containers": 5,
    "chest_count": 3,
    "furnace_count": 2,
    "total_items": 150,
    "cache_info": {
      "chest_cache_size": 3,
      "furnace_cache_size": 2
    }
  }
}
```

## 6. 方块缓存管理

基于方块缓存系统实现，提供方块查询和管理功能。

#### 获取方块缓存统计

````
GET /api/blocks/stats
````

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "获取方块缓存统计成功",
  "data": {
    "total_blocks": 1250,
    "cached_blocks": 1250,
    "memory_usage_mb": 25.6,
    "cache_hit_rate": 0.85,
    "last_cleanup": "2024-01-01T12:00:00Z"
  }
}
```

#### 获取指定区域方块

````
GET /api/blocks/region?x=100&z=200&radius=16
````

**查询参数:**
- `x` (必需): 区域中心X坐标
- `z` (必需): 区域中心Z坐标
- `radius` (可选): 搜索半径，默认16，范围1-64

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "获取区域方块成功",
  "data": {
    "blocks": [
      {
        "position": {
          "x": 100,
          "y": 64,
          "z": 200
        },
        "type": "stone",
        "name": "石头",
        "last_updated": "2024-01-01T12:00:00Z",
        "update_count": 5,
        "distance": 0.0
      }
    ],
    "total": 1,
    "center": {
      "x": 100,
      "z": 200
    },
    "radius": 16
  }
}
```

#### 搜索特定方块

````
GET /api/blocks/search?name=iron_ore&limit=50
````

**查询参数:**
- `name` (必需): 方块名称，支持部分匹配
- `limit` (可选): 返回结果数量限制，默认50，范围1-200

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "搜索方块成功",
  "data": {
    "blocks": [
      {
        "position": {
          "x": 50,
          "y": 30,
          "z": 100
        },
        "type": "iron_ore",
        "name": "铁矿石",
        "last_updated": "2024-01-01T12:00:00Z",
        "update_count": 3
      }
    ],
    "total": 1,
    "search_term": "iron_ore",
    "limit": 50
  }
}
```

#### 获取方块类型统计

````
GET /api/blocks/types
````

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "获取方块类型统计成功",
  "data": {
    "types": [
      {
        "type": "stone",
        "count": 500,
        "names": ["石头"]
      },
      {
        "type": "dirt",
        "count": 300,
        "names": ["泥土"]
      }
    ],
    "total_types": 15
  }
}
```

#### 获取指定位置方块

````
GET /api/blocks/position/{x}/{y}/{z}
````

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "获取位置方块信息成功",
  "data": {
    "position": {
      "x": 100,
      "y": 64,
      "z": 200
    },
    "type": "stone",
    "name": "石头",
    "last_updated": "2024-01-01T12:00:00Z",
    "update_count": 5,
    "exists": true
  }
}
```

#### 清空方块缓存

````
DELETE /api/blocks/cache
````

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "清空方块缓存成功",
  "data": {
    "cleared_blocks": 1250,
    "message": "成功清除了 1250 个方块缓存"
  }
}
```

## 7. MCP 工具管理

基于MCP客户端实现，提供工具元数据获取和工具调用功能。

#### 获取工具元数据

````
GET /api/mcp/tools
````

**响应示例:**

```json
{
  "isSuccess": true,
  "message": "获取工具元数据成功",
  "data": {
    "tools": [
      {
        "name": "move",
        "description": "移动到指定位置",
        "inputSchema": {
          "type": "object",
          "properties": {
            "position": {
              "type": "object",
              "properties": {
                "x": {"type": "number", "description": "目标X坐标"},
                "y": {"type": "number", "description": "目标Y坐标"},
                "z": {"type": "number", "description": "目标Z坐标"}
              },
              "required": ["x", "y", "z"]
            }
          },
          "required": ["position"]
        }
      }
    ],
    "total": 10
  }
}
```

#### 调用工具

````
POST /api/mcp/tools/call
````

**请求体:**

```json
{
  "tool_name": "move",
  "arguments": {
    "position": {
      "x": 123.5,
      "y": 64.0,
      "z": -456.8
    }
  }
}
```

**响应示例 (成功):**

```json
{
  "isSuccess": true,
  "message": "工具调用成功",
  "data": {
    "tool_name": "move",
    "arguments": {
      "position": {
        "x": 123.5,
        "y": 64.0,
        "z": -456.8
      }
    },
    "result": {
      "content": [
        {
          "type": "text",
          "text": "成功移动到位置 (123.5, 64.0, -456.8)"
        }
      ],
      "structured_content": null,
      "is_error": false,
      "data": {
        "success": true,
        "target_position": {
          "x": 123.5,
          "y": 64.0,
          "z": -456.8
        },
        "distance": 5.2,
        "duration": 2.3
      }
    }
  }
}
```

**响应示例 (失败):**

```json
{
  "isSuccess": false,
  "message": "TOOL_ERROR: 移动失败",
  "data": {
    "tool_name": "move",
    "arguments": {
      "position": {
        "x": 123.5,
        "y": 64.0,
        "z": -456.8
      }
    },
    "result": {
      "content": [
        {
          "type": "text",
          "text": "无法到达指定位置"
        }
      ],
      "structured_content": null,
      "is_error": true,
      "data": null
    }
  }
}
```

## 8. 错误处理

### HTTP 错误响应

```json
{
  "isSuccess": false,
  "message": "获取环境快照失败: 玩家位置信息不可用",
  "data": null,
  "timestamp": 1704067200000
}
```

### WebSocket 错误消息

```json
{
  "type": "error",
  "errorCode": "INVALID_INTERVAL",
  "message": "更新间隔必须是非负整数",
  "timestamp": 1704067200000
}
```

**常见错误码:**
- `INVALID_INTERVAL`: 无效的更新间隔
- `UNKNOWN_MESSAGE_TYPE`: 未知消息类型
- `INVALID_JSON`: 无效的JSON格式
- `MESSAGE_PROCESSING_ERROR`: 消息处理失败
- `MCP_NOT_CONNECTED`: MCP客户端未连接
- `TOOL_ERROR`: 工具调用失败
