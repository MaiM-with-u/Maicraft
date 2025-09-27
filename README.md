# Maicraft-Mai

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status](https://img.shields.io/badge/Status-Active-green.svg)](https://github.com/MaiToTheGate/Maicraft-Mai)

一个基于大语言模型的智能Minecraft代理系统，能够自主执行复杂的游戏任务，如挖矿、制作、建造等。
还能与玩家进行流畅的交流，根据玩家的反馈进行行为

## 🎯 项目简介

Maicraft-Mai 是一个智能的Minecraft游戏代理系统，它结合了：
- **大语言模型 (LLM)** - 提供智能决策和任务规划
- **基于Mineflayer的MC操控** 基于maicraft-mcp，操作mc游戏
- **Agent** - 采用ReAct逻辑的Agent

该系统能够理解游戏环境，制定策略，执行简单的MC游玩。
```

## 待实现清单

- 更好的建筑建造和矿道建造
- 基于语音的实时交流
- 与Amaidesu配合，使用tts生成麦麦语音
- 配合MaiCore的插件进行交互

## 📚 文档

- **[🎮 事件系统文档](doc/event-system.md)** - 完整的Maicraft-Mai事件驱动架构指南
  - 支持14种Minecraft原生事件类型
  - 智能中断机制和AI驱动响应
  - 并发安全的事件处理和存储
  - 模块化设计和扩展方式

## 🚀 快速开始

### 环境要求

- Python 3.11+
- Minecraft 服务器

### 安装步骤

1. **克隆仓库**
```bash
git clone https://github.com/MaiM-with-u/Maicraft
cd Maicraft
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置设置**

复制配置模板，将`config-template.toml`复制并更名为`config.toml`

在 `config.toml` 文件中配置以下参数：

```toml
[llm]
model = "gpt-4o-mini"
api_key = "your-openai-api-key"
base_url = "https://api.openai.com/v1"
temperature = 0.2
max_tokens = 1024

[agent]
enabled = true
session_id = "maicraft_default"
max_steps = 50
tick_seconds = 8.0
report_each_step = true

[logging]
level = "INFO"
```

1. **配置服务器**
将`mcp_server/mcp_servers_template.json`复制并更名为`mcp_server/mcp_servers.json`

编辑maicraft-mcp的配置文件，设置你的Minecraft服务器信息
```json
{
  "mcpServers": {
    "maicraft": {
      "command": "npx",
      "args": [
        "-y",
        "maicraft@latest",
        "--host",
        "你的Minecraft服务器地址",     // 例如: "mc.example.com" 或 "192.168.1.100"
        "--port",
        "你的Minecraft服务器端口",     // 例如: "25565" (默认端口)
        "--username",
        "你的游戏用户名",              // 例如: "MaiBot"
        "--auth",
        "offline"                     // 离线模式，或使用 "online" 进行正版验证
      ]
    }
  }
}
```
#### 配置参数说明
- `--host`: Minecraft服务器地址 (IP地址或域名)
- `--port`: 服务器端口 (默认25565)
- `--username`: 游戏用户名
- `--auth`: 认证模式 (`offline` 为离线模式，`online` 为正版验证)

5. **启动系统**
```bash
# Windows
start.cmd

# Linux/Mac
./start.sh

# 或者直接运行
python main.py
```

## Web UI

[maicraft-web-ui](https://github.com/ChangingSelf/maicraft-web-ui)提供了一个简单的 Web UI，用于调试本项目


## 🤝 贡献指南

我们欢迎所有形式的贡献！

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- Minecraft 开发团队
- Mineflayer
- 所有贡献者和用户


## 📞 联系方式

- 项目主页: [GitHub](https://github.com/MaiToTheGate/Maicraft-Mai)
- 问题反馈: [Issues](https://github.com/MaiToTheGate/Maicraft-Mai/issues)
- 讨论交流: [Discussions](https://github.com/MaiToTheGate/Maicraft-Mai/discussions)

---

**注意**: 这是一个实验性项目，请在使用前仔细阅读文档并测试功能。建议在测试环境中使用，避免影响正式的游戏存档。
