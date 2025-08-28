"""
方块缓存预览窗口（pygame）
每 3 秒从 BlockCache 重渲染一次并刷新窗口显示。
"""
from __future__ import annotations

import asyncio
import time
from typing import Optional, Tuple
import threading
import os
import sys
import traceback

# 设置Python路径，确保模块导入正常
if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

try:
    import pygame
except ImportError as e:
    print(f"错误：无法导入 pygame 模块: {e}")
    print("请安装 pygame: pip install pygame")
    sys.exit(1)

try:
    from view_render.renderer import BlockCacheRenderer, RenderConfig
except ImportError as e:
    print(f"错误：无法导入渲染器模块: {e}")
    print("请检查 view_render 模块是否正确安装")
    sys.exit(1)

try:
    from agent.environment import global_environment
except ImportError as e:
    print(f"警告：无法导入环境模块: {e}")
    global_environment = None

try:
    from utils.logger import get_logger
    logger = get_logger("BlockCacheViewer")
except ImportError as e:
    print(f"警告：无法导入日志模块: {e}")
    # 创建一个简单的日志器
    class SimpleLogger:
        def info(self, msg): print(f"[INFO] {msg}")
        def warning(self, msg): print(f"[WARNING] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
        def debug(self, msg): print(f"[DEBUG] {msg}")
    logger = SimpleLogger()

class BlockCacheViewer:
    def __init__(self,
                 renderer: Optional[BlockCacheRenderer] = None,
                 update_interval_seconds: float = 3.0,
                 render_mode: str = "isometric") -> None:
        try:
            self.renderer = renderer or BlockCacheRenderer()
            logger.info("渲染器初始化成功")
        except Exception as e:
            logger.error(f"渲染器初始化失败: {e}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            raise RuntimeError(f"无法初始化渲染器: {e}")
            
        self.update_interval_seconds = update_interval_seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._async_task: Optional[asyncio.Task] = None
        
        # 设置渲染模式
        if render_mode in ["isometric", "first_person"]:
            self.renderer.config.render_mode = render_mode
            logger.info(f"设置渲染模式: {render_mode}")
        else:
            logger.warning(f"未知的渲染模式: {render_mode}，使用默认等距渲染")
            self.renderer.config.render_mode = "isometric"

    def run(self,
            center: Optional[Tuple[float, float, float]] = None,
            radius: Optional[float] = None) -> None:
        try:
            cfg: RenderConfig = self.renderer.config
            logger.info(f"启动渲染窗口，尺寸: {cfg.image_width}x{cfg.image_height}")
            
            pygame.init()
            window = pygame.display.set_mode((cfg.image_width, cfg.image_height))
            pygame.display.set_caption("Block Cache Preview")
            clock = pygame.time.Clock()

            self._running = True
            last_render_time = 0.0
            surface: Optional[pygame.Surface] = None
            render_attempts = 0
            max_render_attempts = 5  # 增加重试次数

            while self._running:
                try:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            self._running = False
                        elif event.type == pygame.KEYDOWN:
                            if event.key in (pygame.K_ESCAPE, pygame.K_q):
                                self._running = False
                            elif event.key == pygame.K_i:
                                # 切换渲染模式
                                current_mode = self.renderer.config.render_mode
                                if current_mode == "isometric":
                                    self.renderer.config.render_mode = "first_person"
                                    logger.info("切换到第一人称渲染模式")
                                else:
                                    self.renderer.config.render_mode = "isometric"
                                    logger.info("切换到等距投影渲染模式")
                                # 强制重新渲染
                                surface = None
                                last_render_time = 0.0
                            elif event.key == pygame.K_r:
                                # 强制重新渲染
                                surface = None
                                last_render_time = 0.0
                                logger.info("强制重新渲染")
                except Exception as e:
                    logger.error(f"事件处理错误: {e}")
                    break

                try:
                    now = time.time()
                    if surface is None or (now - last_render_time) >= self.update_interval_seconds:
                        try:
                            logger.info("开始渲染...")
                            img = self.renderer.render(center=center, radius=radius)
                            if img is None:
                                logger.error("渲染器返回了空图像")
                                render_attempts += 1
                                if render_attempts >= max_render_attempts:
                                    logger.error("渲染失败次数过多，创建默认图像")
                                    # 创建一个默认的错误图像
                                    img = self._create_error_image(cfg.image_width, cfg.image_height)
                                    if img is None:
                                        logger.error("无法创建默认图像，退出程序")
                                        break
                                else:
                                    continue
                            
                            mode = img.mode
                            data = img.tobytes()
                            surface = pygame.image.fromstring(data, img.size, mode).convert_alpha()
                            last_render_time = now
                            render_attempts = 0  # 重置失败计数
                            logger.info("渲染完成")
                        except Exception as render_error:
                            logger.error(f"渲染过程出错: {render_error}")
                            logger.error(f"渲染错误详情: {traceback.format_exc()}")
                            render_attempts += 1
                            if render_attempts >= max_render_attempts:
                                logger.error("渲染失败次数过多，退出程序")
                                break
                            continue

                    if surface is not None:
                        window.blit(surface, (0, 0))
                        pygame.display.flip()
                    clock.tick(60)
                except Exception as e:
                    logger.error(f"主循环错误: {e}")
                    logger.error(f"主循环错误详情: {traceback.format_exc()}")
                    break

        except Exception as e:
            logger.error(f"渲染窗口运行错误: {e}")
            logger.error(f"运行错误详情: {traceback.format_exc()}")
        finally:
            try:
                pygame.quit()
                logger.info("pygame已关闭")
            except Exception as e:
                logger.error(f"关闭pygame时出错: {e}")

    def _create_error_image(self, width: int, height: int):
        """创建一个错误提示图像"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # 创建红色背景的图像
            img = Image.new('RGB', (width, height), color='red')
            draw = ImageDraw.Draw(img)
            
            # 尝试使用默认字体
            try:
                font = ImageFont.load_default()
            except:
                font = None
            
            # 绘制错误信息
            text = "渲染错误\n请检查日志"
            text_color = 'white'
            
            # 计算文本位置（居中）
            if font:
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            else:
                text_width = len(text) * 10
                text_height = 20
            
            x = (width - text_width) // 2
            y = (height - text_height) // 2
            
            if font:
                draw.text((x, y), text, fill=text_color, font=font)
            else:
                # 如果没有字体，绘制简单的矩形
                draw.rectangle([x-5, y-5, x+text_width+5, y+text_height+5], outline='white', width=2)
            
            logger.info("创建了错误提示图像")
            return img
            
        except Exception as e:
            logger.error(f"创建错误图像失败: {e}")
            return None
    async def run_loop(self):
        while False:
            await self.update_overview()
            await asyncio.sleep(20)

    async def run_async(self,
                        center: Optional[Tuple[float, float, float]] = None,
                        radius: Optional[float] = None) -> None:
        """在主事件循环中运行pygame窗口，便于优雅退出。
        注意：应由主线程的 asyncio 事件循环启动。
        """
        cfg: RenderConfig = self.renderer.config
        pygame.init()
        window = pygame.display.set_mode((cfg.image_width, cfg.image_height))
        pygame.display.set_caption("Block Cache Preview")
        clock = pygame.time.Clock()

        self._running = True
        last_render_time = 0.0
        surface: Optional[pygame.Surface] = None

        try:
            while self._running:
                try:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            self._running = False
                        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
                            self._running = False
                except Exception:
                    break

                try:
                    now = time.time()
                    if surface is None or (now - last_render_time) >= self.update_interval_seconds:
                        try:
                            img = self.renderer.render(center=center, radius=radius)
                            if img is not None:
                                mode = img.mode
                                data = img.tobytes()
                                surface = pygame.image.fromstring(data, img.size, mode).convert_alpha()
                                last_render_time = now
                            else:
                                logger.warning("渲染器返回了空图像")
                        except Exception as render_error:
                            logger.error(f"渲染过程出错: {render_error}")
                            continue

                    if surface is not None:
                        window.blit(surface, (0, 0))
                        pygame.display.flip()
                    # 使用tick限制帧率，并交还控制给事件循环
                    clock.tick(60)
                except Exception as e:
                    logger.error(f"主循环错误: {e}")
                    break

                await asyncio.sleep(0)  # 让出控制权，避免阻塞
        finally:
            try:
                pygame.quit()
            except Exception:
                pass
    
    def stop(self) -> None:
        """请求停止预览器并关闭窗口。"""
        try:
            self._running = False
            if pygame.get_init():
                try:
                    # 仅投递一个QUIT事件来唤醒事件循环，真正的退出在运行线程末尾执行
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
                except Exception:
                    pass
        except Exception:
            pass

    def start_in_thread(self) -> None:
        """以独立线程启动，便于优雅退出时 join。"""
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self.run, daemon=False)
        self._thread.start()

    def join(self, timeout: Optional[float] = None) -> None:
        try:
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=timeout)
        except Exception:
            pass

    async def update_overview(self):
        renderer = self.renderer
        renderer.render_to_base64()
        image_base64 = renderer.get_last_render_base64(image_format="PNG", data_uri=True)
        global_environment.overview_base64 = image_base64
        await global_environment.get_overview_str()


__all__ = ["BlockCacheViewer"]


if __name__ == "__main__":
    def main():
        """独立启动方块缓存预览窗口"""
        try:
            # 设置工作路径为上级目录（项目根目录）
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            os.chdir(project_root)
            
            print(f"设置工作路径: {project_root}")
            print("启动方块缓存预览窗口...")
            print("控制说明:")
            print("  ESC 或 Q 键: 退出")
            print("  I 键: 切换渲染模式 (等距投影 ↔ 第一人称)")
            print("  R 键: 强制重新渲染")
            print("  点击窗口关闭按钮: 退出")
            print()
            
            # 检查依赖
            print("检查依赖模块...")
            try:
                import pygame
                print("✓ pygame 模块可用")
            except ImportError as e:
                print(f"✗ pygame 模块不可用: {e}")
                return
            
            try:
                from view_render.renderer import BlockCacheRenderer
                print("✓ 渲染器模块可用")
            except ImportError as e:
                print(f"✗ 渲染器模块不可用: {e}")
                return
            
            # 询问用户选择渲染模式
            while True:
                mode = input("选择渲染模式 (1: 等距投影, 2: 第一人称) [默认: 1]: ").strip()
                if not mode:
                    mode = "1"
                if mode in ["1", "2"]:
                    break
                print("请输入 1 或 2")
            
            render_mode = "isometric" if mode == "1" else "first_person"
            print(f"选择渲染模式: {render_mode}")
            
            # 创建预览器实例
            print("初始化渲染器...")
            try:
                viewer = BlockCacheViewer(update_interval_seconds=3.0, render_mode=render_mode)
                print("✓ 渲染器初始化成功")
            except Exception as e:
                print(f"✗ 渲染器初始化失败: {e}")
                print("错误详情:")
                traceback.print_exc()
                print("\n尝试诊断问题...")
                
                # 尝试单独测试渲染器
                try:
                    from view_render.renderer import BlockCacheRenderer
                    print("测试渲染器创建...")
                    test_renderer = BlockCacheRenderer()
                    print("✓ 测试渲染器创建成功")
                    
                    # 测试配置
                    config = test_renderer.config
                    print(f"  - 图像宽度: {config.image_width}")
                    print(f"  - 图像高度: {config.image_height}")
                    print(f"  - 渲染模式: {config.render_mode}")
                    
                except Exception as test_e:
                    print(f"✗ 测试渲染器也失败: {test_e}")
                    print("这可能是渲染器模块本身的问题")
                
                return
            
            # 启动预览窗口
            print("启动预览窗口...")
            viewer.run()
            
        except KeyboardInterrupt:
            print("\n程序被用户中断")
        except Exception as e:
            print(f"程序运行出错: {e}")
            print("错误详情:")
            traceback.print_exc()
            if 'logger' in locals():
                try:
                    logger.error(f"程序运行出错: {e}", exc_info=True)
                except:
                    pass
        finally:
            print("预览窗口已关闭")
    
    main()


