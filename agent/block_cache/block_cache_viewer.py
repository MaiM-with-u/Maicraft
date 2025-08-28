"""
方块缓存预览窗口（pygame）
每 3 秒从 BlockCache 重渲染一次并刷新窗口显示。
"""
from __future__ import annotations

import asyncio
import time
from typing import Optional, Tuple
import threading
import asyncio

import pygame

from .renderer import BlockCacheRenderer, RenderConfig
from agent.environment import global_environment
from utils.logger import get_logger

logger = get_logger("BlockCacheViewer")

class BlockCacheViewer:
    def __init__(self,
                 renderer: Optional[BlockCacheRenderer] = None,
                 update_interval_seconds: float = 3.0) -> None:
        self.renderer = renderer or BlockCacheRenderer()
        self.update_interval_seconds = update_interval_seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._async_task: Optional[asyncio.Task] = None

    def run(self,
            center: Optional[Tuple[float, float, float]] = None,
            radius: Optional[float] = None) -> None:
        cfg: RenderConfig = self.renderer.config
        

        pygame.init()
        window = pygame.display.set_mode((cfg.image_width, cfg.image_height))
        pygame.display.set_caption("Block Cache Preview")
        clock = pygame.time.Clock()

        self._running = True
        last_render_time = 0.0
        surface: Optional[pygame.Surface] = None

        while self._running:
            try:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self._running = False
                    elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
                        self._running = False
            except Exception:
                # 事件系统已关闭，退出循环
                break

            try:
                now = time.time()
                if surface is None or (now - last_render_time) >= self.update_interval_seconds:
                    img = self.renderer.render(center=center, radius=radius)
                    mode = img.mode
                    data = img.tobytes()
                    surface = pygame.image.fromstring(data, img.size, mode).convert_alpha()
                    last_render_time = now

                window.blit(surface, (0, 0))
                pygame.display.flip()
                clock.tick(60)
            except Exception:
                # 显示或surface已被关闭，退出
                break

        pygame.quit()
        
    
        
    
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
                        img = self.renderer.render(center=center, radius=radius)
                        mode = img.mode
                        data = img.tobytes()
                        surface = pygame.image.fromstring(data, img.size, mode).convert_alpha()
                        last_render_time = now

                    window.blit(surface, (0, 0))
                    pygame.display.flip()
                    # 使用tick限制帧率，并交还控制给事件循环
                    clock.tick(60)
                except Exception:
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


