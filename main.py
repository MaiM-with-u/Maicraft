import asyncio

from config import global_config
from mcp_server.client import global_mcp_client
from utils.logger import setup_advanced_logging
from agent.block_cache.block_cache import global_block_cache

from agent.mai_chat import mai_chat
from agent.environment.movement import global_movement




async def main() -> None:
    # 初始化日志系统
    try:
        setup_advanced_logging(
            level=global_config.logging.level,
            enable_json=global_config.logging.enable_json,
            log_to_file=global_config.logging.log_to_file,
            log_dir=global_config.logging.log_dir,
            rotation=global_config.logging.rotation,
            retention=global_config.logging.retention,
            enable_hierarchical_logging=global_config.logging.enable_hierarchical_logging,
            max_recent_logs=global_config.logging.max_recent_logs,
        )
    except Exception:
        # 忽略日志初始化错误
        pass

    
    # 延迟导入以避免模块顶层导入顺序告警
    from agent.mai_agent import MaiAgent
    
    connected = await global_mcp_client.connect()
    if not connected:
        print("[启动] 无法连接 MCP 服务器，退出")
        return

    agent = MaiAgent()
    await agent.initialize()
    await agent.start()
    
    await mai_chat.start()
    
    await global_block_cache.start_auto_save()
    
    await global_movement.run_speed_monitor()
    
    
    print("[启动] Maicraft-Mai 已启动，按 Ctrl+C 退出")
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit, asyncio.CancelledError):
        # 优雅退出：通知Agent停止并断开MCP
        try:
            if hasattr(agent, "shutdown") and callable(getattr(agent, "shutdown")):
                await agent.shutdown()
        except Exception:
            pass
    finally:
        # 兜底：强制关闭 pygame 窗口，防止残留窗口阻塞退出
        try:
            import pygame  # type: ignore
            try:
                if pygame.get_init():
                    try:
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                    except Exception:
                        pass
                    try:
                        pygame.display.quit()
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                pygame.quit()
            except Exception:
                pass
        except Exception:
            pass
        await global_mcp_client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # 抑制 Ctrl+C 的冗长堆栈，保持静默优雅退出
        pass
