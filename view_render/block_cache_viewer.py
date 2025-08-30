"""
方块缓存预览窗口（pygame）
每 3 秒从 BlockCache 重渲染一次并刷新窗口显示。
"""
from __future__ import annotations

import asyncio
import time
import threading
from typing import Optional, Tuple

import pygame

from view_render.renderer import BlockCacheRenderer, RenderConfig
from agent.environment.environment import global_environment
from utils.logger import get_logger

logger = get_logger("BlockCacheViewer")

class BlockCacheViewer:
    def __init__(self,
                 renderer: Optional[BlockCacheRenderer] = None,
                 update_interval_seconds: float = 3.0) -> None:
        self.renderer = renderer or BlockCacheRenderer()
        self.update_interval_seconds = update_interval_seconds
        self._running = False
        self._thread = None

    def run(self,
            center: Optional[Tuple[float, float, float]] = None,
            radius: Optional[float] = None) -> None:
        """同步运行方法，在主线程中运行"""
        cfg: RenderConfig = self.renderer.config
        

        pygame.init()
        window = pygame.display.set_mode((cfg.image_width, cfg.image_height))
        pygame.display.set_caption("Block Cache Preview")
        clock = pygame.time.Clock()

        self._running = True
        last_render_time = 0.0
        surface: Optional[pygame.Surface] = None

        while self._running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
                    self._running = False

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

        pygame.quit()

    def run_in_thread(self,
                     center: Optional[Tuple[float, float, float]] = None,
                     radius: Optional[float] = None) -> None:
        """在单独线程中运行，防止阻塞主线程"""
        if self._thread and self._thread.is_alive():
            logger.warning("BlockCacheViewer 已在运行中")
            return
        
        self._thread = threading.Thread(
            target=self.run,
            args=(center, radius),
            daemon=True,  # 设为守护线程，主程序退出时自动结束
            name="BlockCacheViewer-Thread"
        )
        self._thread.start()
        logger.info("BlockCacheViewer 已在单独线程中启动")

    def stop(self) -> None:
        """停止预览窗口"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)  # 等待最多2秒
            logger.info("BlockCacheViewer 已停止")
    
    async def run_loop(self):
        """异步循环方法，用于定期更新概览"""
        while True:
            try:
                await self.update_overview()
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"run_loop 异常: {e}")
                await asyncio.sleep(5)  # 出错时等待5秒再继续
    
    async def update_overview(self):
        """更新概览图像"""
        try:
            renderer = self.renderer
            renderer.render_to_base64()
            image_base64 = renderer.get_last_render_base64(image_format="PNG", data_uri=True, compress_ratio=0.25)
            global_environment.overview_base64 = image_base64
            await global_environment.get_overview_str()
        except Exception as e:
            logger.error(f"update_overview 异常: {e}")


__all__ = ["BlockCacheViewer"]


