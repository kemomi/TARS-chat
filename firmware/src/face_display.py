# -*- coding: utf-8 -*-
"""
表情显示模块
基于 Pygame 在 HDMI / 树莓派 DSI 屏 / SPI LCD 上渲染表情。
也支持将帧通过 WebSocket 推给 Web 端 (低 FPS) 作为预览。

表情资源约定:
  assets/faces/
    neutral/  -> 0001.png, 0002.png ...  (循环播放眨眼)
    happy/
    sad/
    angry/
    surprised/
    sleepy/
若某个目录只有单张 still.png,则静态显示。
"""
import logging
import os
import threading
import time
from pathlib import Path

logger = logging.getLogger("face")

try:
    import pygame
    _HAS_PYGAME = True
except ImportError:
    pygame = None
    _HAS_PYGAME = False
    logger.warning("未安装 pygame, 表情仅记录到日志")


class FaceDisplay:
    def __init__(self, width: int = 320, height: int = 240,
                 fullscreen: bool = True, assets_dir: str = "assets/faces"):
        self.width = width
        self.height = height
        self.assets_dir = Path(__file__).parent.parent / assets_dir
        self._current = "neutral"
        self._lock = threading.Lock()
        self._frames_cache = {}   # expression -> [Surface, ...]
        self._running = True
        self._anim_thread = None

        if _HAS_PYGAME:
            os.environ.setdefault("SDL_VIDEODRIVER", "x11")  # 改为 'kmsdrm' 可脱离桌面环境
            pygame.init()
            flags = pygame.FULLSCREEN if fullscreen else 0
            self.screen = pygame.display.set_mode((width, height), flags)
            pygame.display.set_caption("TARS-chat Face")
            pygame.mouse.set_visible(False)
            self._preload()
            self._start_anim_loop()
        else:
            self.screen = None

    # ---------- 资源加载 ----------
    def _preload(self):
        if not self.assets_dir.exists():
            logger.warning(f"表情资源目录不存在: {self.assets_dir}, 将渲染占位文本")
            return
        for emo_dir in self.assets_dir.iterdir():
            if not emo_dir.is_dir():
                continue
            frames = []
            for img_path in sorted(emo_dir.glob("*.png")):
                try:
                    surf = pygame.image.load(str(img_path)).convert_alpha()
                    surf = pygame.transform.scale(surf, (self.width, self.height))
                    frames.append(surf)
                except Exception as e:
                    logger.error(f"加载 {img_path} 失败: {e}")
            if frames:
                self._frames_cache[emo_dir.name] = frames
                logger.info(f"  加载表情 {emo_dir.name}: {len(frames)} 帧")

    # ---------- 动画循环 ----------
    def _start_anim_loop(self):
        self._anim_thread = threading.Thread(target=self._anim_loop, daemon=True)
        self._anim_thread.start()

    def _anim_loop(self):
        clock = pygame.time.Clock()
        frame_idx = 0
        while self._running:
            with self._lock:
                emo = self._current
                frames = self._frames_cache.get(emo, [])
            if frames:
                surf = frames[frame_idx % len(frames)]
                self.screen.blit(surf, (0, 0))
            else:
                self._render_placeholder(emo)
            pygame.display.flip()
            frame_idx += 1
            clock.tick(10)  # 10 FPS,够用且省电

            # 抽干事件队列防止系统假死
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False

    def _render_placeholder(self, emo: str):
        self.screen.fill((20, 20, 30))
        font = pygame.font.SysFont("monospace", 32, bold=True)
        text = font.render(f":: {emo} ::", True, (0, 255, 180))
        rect = text.get_rect(center=(self.width // 2, self.height // 2))
        self.screen.blit(text, rect)

    # ---------- 公共 API ----------
    def show(self, expression: str):
        with self._lock:
            if expression not in self._frames_cache and not _HAS_PYGAME:
                logger.info(f"[MOCK] 表情切换: {expression}")
            self._current = expression
        logger.info(f"表情 -> {expression}")

    @property
    def current(self) -> str:
        return self._current

    @property
    def available(self) -> list:
        return list(self._frames_cache.keys()) or [
            "neutral", "happy", "sad", "angry", "surprised", "sleepy"
        ]

    def cleanup(self):
        self._running = False
        if _HAS_PYGAME:
            try:
                pygame.quit()
            except Exception:
                pass