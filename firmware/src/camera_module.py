# -*- coding: utf-8 -*-
"""
摄像头模块
=========
支持两种后端,启动时自动探测:
  1. picamera2  -> 树莓派官方 CSI 摄像头 (Camera Module v1/v2/v3, HQ Camera)
  2. opencv     -> USB 摄像头 (V4L2)
若都不可用,启用 mock 模式 (回传一张占位图)
"""
import logging
import threading
import time
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger("camera")

# ---------- 后端探测 ----------
try:
    from picamera2 import Picamera2
    _BACKEND = "picamera2"
except ImportError:
    Picamera2 = None
    try:
        import cv2
        _BACKEND = "opencv"
    except ImportError:
        cv2 = None
        _BACKEND = "mock"
        logger.warning("未检测到 picamera2 / opencv, 摄像头进入 mock 模式")
# opencv 即便走 picamera2 后端也要用 (画框、编码)
try:
    import cv2 as _cv2
except ImportError:
    _cv2 = None


class CameraModule:
    """统一摄像头接口,内部双缓冲 + 后台采集线程"""

    def __init__(self, width: int = 640, height: int = 480, fps: int = 15,
                 device_index: int = 0):
        self.width = width
        self.height = height
        self.fps = fps
        self.device_index = device_index
        self._frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._cam = None
        self._init_backend()

    def _init_backend(self):
        if _BACKEND == "picamera2":
            try:
                self._cam = Picamera2()
                cfg = self._cam.create_video_configuration(
                    main={"size": (self.width, self.height), "format": "RGB888"},
                )
                self._cam.configure(cfg)
                self._cam.start()
                logger.info(f"picamera2 启动: {self.width}x{self.height}@{self.fps}fps")
            except Exception as e:
                logger.error(f"picamera2 初始化失败: {e}")
                self._cam = None

        elif _BACKEND == "opencv":
            self._cam = _cv2.VideoCapture(self.device_index)
            self._cam.set(_cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self._cam.set(_cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self._cam.set(_cv2.CAP_PROP_FPS, self.fps)
            if not self._cam.isOpened():
                logger.error("opencv: 无法打开摄像头")
                self._cam = None
            else:
                logger.info(f"opencv 摄像头启动 (device={self.device_index})")

    def start(self):
        """启动后台采集线程"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info("摄像头采集线程启动")

    def _capture_loop(self):
        interval = 1.0 / self.fps
        while self._running:
            t0 = time.time()
            frame = self._grab()
            if frame is not None:
                with self._lock:
                    self._frame = frame
            elapsed = time.time() - t0
            time.sleep(max(0, interval - elapsed))

    def _grab(self) -> Optional[np.ndarray]:
        """采集一帧, 统一返回 BGR 格式 (OpenCV 习惯)"""
        if _BACKEND == "picamera2" and self._cam:
            arr = self._cam.capture_array()  # RGB
            if _cv2:
                return _cv2.cvtColor(arr, _cv2.COLOR_RGB2BGR)
            return arr
        elif _BACKEND == "opencv" and self._cam:
            ok, frame = self._cam.read()
            return frame if ok else None
        else:
            # mock: 返回一帧渐变图
            t = time.time()
            mock = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            mock[:] = (40, int(40 + 30 * np.sin(t)), 60)
            if _cv2:
                _cv2.putText(mock, "NO CAMERA (mock)",
                             (self.width // 2 - 120, self.height // 2),
                             _cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 180), 2)
            return mock

    def read(self) -> Optional[np.ndarray]:
        """读取最新一帧 (拷贝)"""
        with self._lock:
            return None if self._frame is None else self._frame.copy()

    def jpeg(self, quality: int = 70) -> Optional[bytes]:
        """编码为 JPEG (用于 MJPEG 推流)"""
        frame = self.read()
        if frame is None or _cv2 is None:
            return None
        ok, buf = _cv2.imencode(".jpg", frame, [_cv2.IMWRITE_JPEG_QUALITY, quality])
        return buf.tobytes() if ok else None

    def snapshot_base64(self) -> Optional[str]:
        """拍照,返回 base64 JPEG (用于喂给 vision LLM)"""
        import base64
        b = self.jpeg(quality=85)
        return base64.b64encode(b).decode("ascii") if b else None

    @property
    def backend(self) -> str:
        return _BACKEND

    def cleanup(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        try:
            if _BACKEND == "picamera2" and self._cam:
                self._cam.stop()
            elif _BACKEND == "opencv" and self._cam:
                self._cam.release()
        except Exception as e:
            logger.error(f"摄像头清理失败: {e}")
