import asyncio

from config import global_config
from mcp_server.client import global_mcp_client
from utils.logger import setup_advanced_logging, get_logger
from agent.block_cache.block_cache import global_block_cache

from agent.mai_chat import mai_chat
from agent.environment.movement import global_movement

# 导入API服务器
from api import get_api_server

# 获取当前模块的日志器
logger = get_logger("Main")




async def run_main_agent() -> None:
    """运行主要的MaicraftAgent逻辑"""
    # 延迟导入以避免模块顶层导入顺序告警
    from agent.mai_agent import MaiAgent

    # 连接到MCP服务器，启用自动重连
    logger.info("正在连接到 MCP 服务器...")
    connected = await global_mcp_client.connect(enable_auto_reconnect=True)
    if not connected:
        logger.error("无法连接 MCP 服务器，程序将继续运行，重连机制已启用")
        # 不立即退出，让程序继续运行，依赖重连机制

    agent = MaiAgent()
    try:
        logger.info("正在初始化 MaiAgent...")
        await agent.initialize()

        # 在MaiAgent初始化后设置事件处理器，避免循环依赖
        from agent.events import setup_event_handlers
        setup_event_handlers()
        logger.info("事件处理器设置完成")

        logger.info("MaiAgent 初始化完成")
    except Exception as e:
        logger.error(f"MaiAgent 初始化失败: {e}")
        import traceback
        logger.error(f"初始化异常详情: {traceback.format_exc()}")
        return

    try:
        logger.info("正在启动 MaiAgent...")
        await agent.start()
        logger.info("MaiAgent 启动完成")
    except Exception as e:
        logger.error(f"MaiAgent 启动失败: {e}")
        import traceback
        logger.error(f"启动异常详情: {traceback.format_exc()}")
        return

    await mai_chat.start()

    await global_block_cache.start_auto_save()

    await global_movement.run_speed_monitor()

    logger.info("Maicraft-Mai 已启动，按 Ctrl+C 退出")
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
        # 优雅关闭MCP客户端
        logger.info("正在关闭 MCP 客户端...")
        try:
            await global_mcp_client.shutdown()
        except Exception as e:
            logger.error(f"关闭MCP客户端时发生异常: {e}")

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


async def run_websocket_server() -> None:
    """运行WebSocket API服务器"""
    import uvicorn
    from api import create_app

    try:
        # 获取API服务器实例
        logger.info("正在初始化API服务器...")
        api_server = get_api_server()
        logger.info("API服务器实例创建成功")

        # 从API配置获取服务器设置
        from api.config import api_config as api_server_config, update_api_config_from_global

        # 更新API配置以使用全局配置
        update_api_config_from_global()

        host = api_server_config.server.host
        port = api_server_config.server.port
        log_level = api_server_config.server.log_level

        logger.info("正在启动WebSocket API服务器...")
        logger.info(f"WebSocket地址: ws://{host}:{port}/ws/logs")
        logger.info(f"REST API地址: http://{host}:{port}/api/")
        logger.info(f"服务器配置: 主机={host}, 端口={port}, 日志级别={log_level}")

        # 创建FastAPI应用
        logger.info("正在创建FastAPI应用...")
        app = create_app()
        logger.info("FastAPI应用创建成功")

        # 配置uvicorn服务器
        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level=log_level,  # 使用配置中的日志级别
            access_log=False      # 关闭访问日志
        )

        server = uvicorn.Server(config)
        logger.info("正在启动uvicorn服务器...")

        await server.serve()
    except Exception as e:
        logger.error(f"WebSocket服务器启动失败: {e}")
        import traceback
        logger.error(f"详细错误信息: {traceback.format_exc()}")
        raise
    finally:
        logger.info("WebSocket服务器已关闭")


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

    logger.info("正在启动 Maicraft-Mai 和 WebSocket API 服务器...")

    try:
        # 并发运行两个服务
        await asyncio.gather(
            run_main_agent(),
            run_websocket_server(),
            return_exceptions=True  # 如果一个任务出错，允许其他任务继续运行
        )
    except (KeyboardInterrupt, SystemExit, asyncio.CancelledError):
        logger.info("接收到退出信号，正在关闭服务...")
    except Exception as e:
        logger.error(f"启动过程中发生错误: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # 抑制 Ctrl+C 的冗长堆栈，保持静默优雅退出
        pass
