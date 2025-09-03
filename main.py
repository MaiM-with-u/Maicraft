import asyncio
import os
from typing import Any, Dict
import tomli

from mcp_server.client import MCPClient
from config import global_config
from mcp_server.client import global_mcp_client
from utils.logger import setup_logging, get_logger
from view_render.renderer_3d import get_global_renderer_3d, stop_3d_renderer




async def main() -> None:
    # 初始化日志级别
    try:
        setup_logging(global_config.logging.level)
    except Exception:
        # 忽略日志初始化错误
        pass


    # 设置渲染器模式 - 必须在Agent初始化之前设置！
    # 注意：3D渲染器和2D预览窗口（BlockCacheViewer）不能同时运行，因为pygame一次只能启动一个窗口
    enable_3d_renderer = True  # 启动3D渲染器
    enable_2d_viewer = False   # 禁用2D预览窗口

    # 在Agent初始化之前设置环境变量，防止2D预览窗口启动
    if enable_3d_renderer:
        os.environ['DISABLE_2D_VIEWER'] = '1'
        print("[启动] 2D预览窗口已被禁用（3D渲染器模式）")

    # 延迟导入以避免模块顶层导入顺序告警
    from agent.mai_agent import MaiAgent
    from agent.action.craft_action.craft_action import recipe_finder

    connected = await global_mcp_client.connect()
    if not connected:
        print("[启动] 无法连接 MCP 服务器，退出")
        return



    # 让配方系统可用
    recipe_finder.mcp_client = global_mcp_client

    agent = MaiAgent()
    await agent.initialize()

    if enable_3d_renderer:
        try:
            # 直接启动3D渲染器（已经在渲染器内部使用daemon线程）
            renderer_3d = get_global_renderer_3d()
            success = renderer_3d.start()
            if success:
                print("[启动] 3D渲染器已启动")
                # 禁用2D预览窗口
                enable_2d_viewer = False
            else:
                print("[启动] 3D渲染器线程启动失败")
                print("[启动] 将尝试启动2D预览窗口作为替代")
                enable_2d_viewer = True
                # 如果3D渲染器启动失败，允许2D预览窗口启动
                os.environ.pop('DISABLE_2D_VIEWER', None)
        except Exception as e:
            print(f"[启动] 3D渲染器启动失败: {e}")
            print("[启动] 3D渲染器启动失败可能原因: 缺少PyOpenGL或显卡驱动问题")
            print("[启动] 将尝试启动2D预览窗口作为替代")
            enable_2d_viewer = True
            # 如果3D渲染器启动失败，允许2D预览窗口启动
            os.environ.pop('DISABLE_2D_VIEWER', None)
    else:
        print("[启动] 3D渲染器已禁用")
        enable_2d_viewer = True

    # 启动两个主循环
    # plan_task = asyncio.create_task(agent.run_plan_loop())
    exec_task = asyncio.create_task(agent.run_execute_loop())
    agent.exec_task = exec_task

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
        # 停止3D渲染器
        try:
            stop_3d_renderer()
            print("[退出] 3D渲染器已停止")
        except Exception:
            pass
            
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
