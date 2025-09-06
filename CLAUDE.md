# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Maicraft-Mai is an intelligent Minecraft agent system that combines LLM-based decision making with MCP (Model Context Protocol) to enable autonomous gameplay. The system can perform complex tasks like mining, crafting, building, and resource management.

## Essential Commands

### Running the Application
```bash
# Windows (recommended - handles venv setup)
start.cmd

# Windows with conda
start-conda.cmd

# Linux/Mac
./start.sh

# Direct Python execution
python main.py

# Reinstall dependencies and run
start.cmd --reinstall
```

### Testing
```bash
# Test query_area_blocks functionality
python test_query_area_blocks.py

# Test VLM speed
python test_vlm_speed.py
```

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run with logging (set level in config.toml)
# Levels: TRACE, DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL
```

## Architecture Overview

### Core Components

**MaiAgent** (`agent/mai_agent.py`): Main orchestrator that:
- Manages LLM clients (primary, fast, and VLM)
- Coordinates environment updates and action execution
- Handles different operation modes (main, chat, task_edit, GUI)

**Environment System**:
- `global_environment` (`agent/environment/environment.py`): Central state management
- `global_environment_updater` (`agent/environment/environment_updater.py`): Async data collection
- `global_block_cache` (`agent/block_cache/block_cache.py`): Persistent block storage with auto-save

**MCP Integration** (`mcp_server/client.py`):
- FastMCP-based client for Minecraft server communication
- Reads configuration from `mcp_server/mcp_servers.json`
- Provides tools for game state queries and actions

**Action System** (`agent/action/`):
- Modular action handlers (mining, movement, crafting, placement)
- Recipe system with crafting support
- Container interaction (chests, furnaces)

### Key Patterns

**Asynchronous Architecture**: The system heavily uses asyncio for:
- Environment polling (0.2s intervals)
- MCP tool calls
- Concurrent action execution

**Global State Management**: Critical singletons:
- `global_environment`: Game state and player info
- `global_environment_updater`: Data collection coordinator
- `global_block_cache`: Persistent block data
- `global_mcp_client`: MCP connection manager
- `global_thinking_log`: Agent decision tracking

**Mode-Based Operation**: The agent operates in different modes:
- `main_mode`: General gameplay and task execution
- `chat_mode`: Player interaction via chat
- `task_edit_mode`: Task planning and modification
- `chest_gui`/`furnace_gui`: Container interaction modes

## Configuration

### MCP Server Configuration
Critical for Minecraft connection - edit `mcp_server/mcp_servers.json`:
```json
{
  "mcpServers": {
    "minecraft": {
      "command": "npx",
      "args": [
        "-y",
        "maicraft@latest",
        "--host", "your-server-ip",
        "--port", "25565",
        "--username", "bot-name",
        "--auth", "offline"
      ]
    }
  }
}
```

### Application Configuration
Edit `config.toml` for:
- LLM settings (model, API keys, endpoints)
- Bot behavior and goals
- Visual processing options
- Logging levels

## Development Notes

### Block Cache System
- Automatically saves to `data/block_cache.json` every 30 seconds
- Supports position-based queries and type indexing
- Handles `can_see` information from `query_area_blocks` tool
- Implements auto-repair for corrupted cache files


### Action Execution
- Actions are parsed from LLM responses with tool calling format
- Supports movement, mining, crafting, and container operations
- GUI modes handle complex container interactions
- Action results are fed back into the planning loop


## 回复指南
请用中文与我交流，并尽可能使用中文注释

