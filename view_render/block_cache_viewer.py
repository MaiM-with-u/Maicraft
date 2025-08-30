"""
方块缓存预览窗口（pygame）
每 3 秒从 BlockCache 重渲染一次并刷新窗口显示。
"""
from __future__ import annotations

import asyncio
import time
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
        
    
        
    
    async def run_loop(self):
        while False:
            await self.update_overview()
            await asyncio.sleep(20)
    
    async def update_overview(self):
        renderer = self.renderer
        renderer.render_to_base64()
        image_base64 = renderer.get_last_render_base64(image_format="PNG", data_uri=True)
        global_environment.overview_base64 = image_base64
        await global_environment.get_overview_str()


__all__ = ["BlockCacheViewer"]


