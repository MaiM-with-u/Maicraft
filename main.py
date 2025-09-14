import asyncio

from config import global_config
from mcp_server.client import global_mcp_client
from utils.logger import setup_advanced_logging
from agent.block_cache.block_cache import global_block_cache

from agent.mai_chat import mai_chat
from agent.environment.movement import global_movement

# 导入API服务器
from api import get_websocket_server




async def run_main_agent() -> None:
    """运行主要的MaicraftAgent逻辑"""
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


async def run_websocket_server() -> None:
    """运行WebSocket API服务器"""
    import uvicorn
    from api import create_websocket_app

    # 获取API服务器实例
    api_server = get_websocket_server()

    # 从配置获取API服务器设置
    api_config = global_config.api
    host = api_config.host
    port = api_config.port
    log_level = api_config.log_level

    print("[API] WebSocket 日志服务器已启动")
    print(f"📡 WebSocket地址: ws://{host}:{port}/ws/logs")
    print(f"🌐 REST API地址: http://{host}:{port}/api/")
    print(f"🔧 服务器配置: 主机={host}, 端口={port}, 日志级别={log_level}")

    # 创建FastAPI应用
    app = create_websocket_app()

    # 配置uvicorn服务器
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level=log_level,  # 使用配置中的日志级别
        access_log=False      # 关闭访问日志
    )

    server = uvicorn.Server(config)

    try:
        await server.serve()
    except (KeyboardInterrupt, SystemExit, asyncio.CancelledError):
        print("[API] 正在关闭WebSocket服务器...")
        print("[API] WebSocket服务器已关闭")


async def main() -> None:
    """主函数：并发运行MaicraftAgent和WebSocket API服务器"""
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

    print("[启动] 正在启动 Maicraft-Mai 和 WebSocket API 服务器...")

    try:
        # 并发运行两个服务
        await asyncio.gather(
            run_main_agent(),
            run_websocket_server(),
            return_exceptions=True  # 如果一个任务出错，允许其他任务继续运行
        )
    except (KeyboardInterrupt, SystemExit, asyncio.CancelledError):
        print("[启动] 接收到退出信号，正在关闭服务...")
    except Exception as e:
        print(f"[启动] 启动过程中发生错误: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # 抑制 Ctrl+C 的冗长堆栈，保持静默优雅退出
        pass
