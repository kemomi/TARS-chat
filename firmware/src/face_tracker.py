# -*- coding: utf-8 -*-
"""
人脸跟踪
========
- FaceDetector: 基于 OpenCV Haar 级联分类器 (轻量, Pi4 上能跑 ~15fps)
- FaceTracker:  后台线程, 把人脸中心位置反馈给 ServoController, 做 PID 平滑跟踪

替代方案: 若你装了 dlib / mediapipe, 也可在 FaceDetector 里换成那个,精度更高但占用更大。
"""
import logging
import threading
import time
from dataclasses import dataclass
from typing import Optional

try:
    import cv2
    _HAS_CV = True
except ImportError:
    cv2 = None
    _HAS_CV = False

logger = logging.getLogger("face_track")


@dataclass
class FaceBox:
    x: int          # 左上角
    y: int
    w: int
    h: int
    @property
    def cx(self) -> int: return self.x + self.w // 2
    @property
    def cy(self) -> int: return self.y + self.h // 2
    @property
    def area(self) -> int: return self.w * self.h


class FaceDetector:
    """Haar 级联人脸检测。每帧只取最大的一张脸。"""
    def __init__(self, cascade_path: Optional[str] = None,
                 scale_factor: float = 1.2, min_neighbors: int = 5,
                 min_size: int = 60):
        if not _HAS_CV:
            logger.warning("OpenCV 未安装,人脸检测不可用")
            self._cascade = None
            return
        path = cascade_path or (cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        self._cascade = cv2.CascadeClassifier(path)
        if self._cascade.empty():
            raise RuntimeError(f"加载 Haar 模型失败: {path}")
        self.scale_factor = scale_factor
        self.min_neighbors = min_neighbors
        self.min_size = min_size
        logger.info(f"人脸检测器就绪 (Haar {path})")

    def detect(self, frame) -> Optional[FaceBox]:
        if not _HAS_CV or self._cascade is None or frame is None:
            return None
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        faces = self._cascade.detectMultiScale(
            gray,
            scaleFactor=self.scale_factor,
            minNeighbors=self.min_neighbors,
            minSize=(self.min_size, self.min_size),
        )
        if len(faces) == 0:
            return None
        # 选最大那张脸
        x, y, w, h = max(faces, key=lambda b: b[2] * b[3])
        return FaceBox(int(x), int(y), int(w), int(h))

    def draw(self, frame, box: Optional[FaceBox], tracking: bool = False):
        """在帧上画人脸框 + 中心点 + 状态文字"""
        if not _HAS_CV:
            return frame
        h, w = frame.shape[:2]
        # 画面中心十字
        cv2.line(frame, (w//2 - 10, h//2), (w//2 + 10, h//2), (100, 100, 100), 1)
        cv2.line(frame, (w//2, h//2 - 10), (w//2, h//2 + 10), (100, 100, 100), 1)

        if box:
            color = (0, 212, 170) if tracking else (255, 200, 100)
            cv2.rectangle(frame, (box.x, box.y), (box.x + box.w, box.y + box.h), color, 2)
            cv2.circle(frame, (box.cx, box.cy), 4, color, -1)
            # 连线表示偏移
            cv2.line(frame, (w//2, h//2), (box.cx, box.cy), color, 1, cv2.LINE_AA)

        # 状态条
        status = "TRACKING" if tracking else ("LOCKED" if box else "SEARCHING")
        cv2.putText(frame, status, (10, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 212, 170), 2)
        return frame


class FaceTracker:
    """
    后台跟踪线程:
      - 读相机帧 -> 检测人脸 -> 计算偏移 -> 驱动舵机增量
      - 增量比例式控制 (P-only),避免 PID 调参复杂
      - 死区: 中心 ±8% 内不动,避免抖动
      - 失去目标 1.5s 后,回中并停止跟踪
    """
    def __init__(self, camera, detector: FaceDetector, servo,
                 pan_gain: float = 0.05, tilt_gain: float = 0.04,
                 deadzone_pct: float = 0.08, lost_timeout: float = 1.5,
                 detect_fps: int = 10):
        self.camera = camera
        self.detector = detector
        self.servo = servo
        self.pan_gain = pan_gain
        self.tilt_gain = tilt_gain
        self.deadzone_pct = deadzone_pct
        self.lost_timeout = lost_timeout
        self.detect_fps = detect_fps

        self._enabled = False
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_box: Optional[FaceBox] = None
        self._last_seen = 0.0
        self._stats = {"fps": 0.0, "detections": 0, "misses": 0}

    @property
    def enabled(self) -> bool:
        return self._enabled

    def enable(self, on: bool):
        self._enabled = on
        logger.info(f"人脸跟踪 -> {'开启' if on else '关闭'}")
        if not on and self.servo:
            # 关闭时回中
            try:
                self.servo.center()
            except Exception:
                pass

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        interval = 1.0 / self.detect_fps
        last_t = time.time()
        while self._running:
            t0 = time.time()
            frame = self.camera.read()
            box = self.detector.detect(frame) if (self._enabled and frame is not None) else None

            if self._enabled:
                if box:
                    self._on_detect(frame, box)
                    self._stats["detections"] += 1
                else:
                    self._on_lost()
                    self._stats["misses"] += 1

            self._last_box = box  # 用于 MJPEG 画框
            # FPS 统计
            dt = time.time() - last_t
            if dt > 0:
                self._stats["fps"] = 0.9 * self._stats["fps"] + 0.1 * (1.0 / dt)
            last_t = time.time()
            time.sleep(max(0, interval - (time.time() - t0)))

    def _on_detect(self, frame, box: FaceBox):
        h, w = frame.shape[:2]
        # 归一化偏移 [-1, 1]
        err_x = (box.cx - w / 2) / (w / 2)
        err_y = (box.cy - h / 2) / (h / 2)

        if abs(err_x) > self.deadzone_pct or abs(err_y) > self.deadzone_pct:
            # err_x > 0 表示脸在画面右侧 -> 摄像头向右转 -> pan 角度减小
            # (具体方向看你舵机装的方向, 不对就把 gain 改成负号)
            cur = self.servo.status
            new_pan = cur["pan"] - err_x * self.pan_gain * 90
            new_tilt = cur["tilt"] + err_y * self.tilt_gain * 90
            try:
                self.servo.set_pan(new_pan)
                self.servo.set_tilt(new_tilt)
            except Exception as e:
                logger.error(f"舵机驱动失败: {e}")
        self._last_seen = time.time()

    def _on_lost(self):
        if self._last_seen and time.time() - self._last_seen > self.lost_timeout:
            # 长时间没看到,回中等待
            try:
                cur = self.servo.status
                if abs(cur["pan"] - 90) > 5 or abs(cur["tilt"] - 90) > 5:
                    self.servo.smooth_to(90, 90, duration=0.5)
            except Exception:
                pass
            self._last_seen = 0  # 防止反复回中

    @property
    def last_box(self) -> Optional[FaceBox]:
        return self._last_box

    @property
    def stats(self) -> dict:
        return {"enabled": self._enabled, **self._stats}

    def cleanup(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
