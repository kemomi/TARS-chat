#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TARS-chat 主程序入口
==================
启动顺序:
  1. 读取 config.yaml 配置
  2. 初始化舵机控制器 (Pan / Tilt)
  3. 初始化表情显示器 (HDMI / SPI LCD)
  4. 初始化语音模块 (可选)
  5. 初始化摄像头 + 人脸跟踪 (可选)
  6. 初始化 LLM 对话编排器 (可选, 含视觉问答)
  7. 启动 Web 服务 (Flask + Socket.IO)
"""
import logging
import signal
import sys
from pathlib import Path

import yaml

from src.servo_controller import ServoController
from src.face_display import FaceDisplay
from src.voice_module import VoiceModule
from src.llm_provider import create_provider
from src.dialogue import DialogueOrchestrator
from src.web_server import create_app, run_server

# ---------- 日志配置 ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/var/log/tars-chat.log", mode="a", encoding="utf-8"),
    ],
)
logger = logging.getLogger("TARS-main")


def load_config(config_path: str = "config.yaml") -> dict:
    path = Path(__file__).parent / config_path
    if not path.exists():
        logger.error(f"配置文件不存在: {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    logger.info(f"配置加载完成: {path}")
    return cfg


def main():
    logger.info("=" * 50)
    logger.info("TARS-chat 启动中...")
    logger.info("=" * 50)

    cfg = load_config()

    # 1. 舵机
    servo = ServoController(
        pan_pin=cfg["servo"]["pan_pin"],
        tilt_pin=cfg["servo"]["tilt_pin"],
        pan_range=cfg["servo"]["pan_range"],
        tilt_range=cfg["servo"]["tilt_range"],
        freq=cfg["servo"].get("freq", 50),
    )
    servo.center()

    # 2. 表情
    face = FaceDisplay(
        width=cfg["display"]["width"],
        height=cfg["display"]["height"],
        fullscreen=cfg["display"].get("fullscreen", True),
        assets_dir=cfg["display"].get("assets_dir", "assets/faces"),
    )
    face.show("neutral")

    # 3. 语音(可选)
    voice = None
    if cfg.get("voice", {}).get("enabled", False):
        try:
            voice = VoiceModule(
                tts_engine=cfg["voice"].get("tts_engine", "pyttsx3"),
                lang=cfg["voice"].get("lang", "zh"),
            )
        except Exception as e:
            logger.warning(f"语音模块初始化失败,已禁用: {e}")

    # 4. 摄像头 + 人脸跟踪 (可选)
    camera = None
    tracker = None
    if cfg.get("camera", {}).get("enabled", False):
        try:
            from src.camera_module import CameraModule
            from src.face_tracker import FaceDetector, FaceTracker
            cam_cfg = cfg["camera"]
            camera = CameraModule(
                width=cam_cfg.get("width", 640),
                height=cam_cfg.get("height", 480),
                fps=cam_cfg.get("fps", 15),
                device_index=cam_cfg.get("device_index", 0),
            )
            camera.start()
            logger.info(f"摄像头启动: {camera.backend}")

            if cam_cfg.get("tracking", {}).get("enabled", True):
                tk_cfg = cam_cfg["tracking"]
                detector = FaceDetector(min_size=tk_cfg.get("min_face_size", 60))
                tracker = FaceTracker(
                    camera=camera, detector=detector, servo=servo,
                    pan_gain=tk_cfg.get("pan_gain", 0.05),
                    tilt_gain=tk_cfg.get("tilt_gain", 0.04),
                    deadzone_pct=tk_cfg.get("deadzone_pct", 0.08),
                    lost_timeout=tk_cfg.get("lost_timeout", 1.5),
                    detect_fps=tk_cfg.get("detect_fps", 10),
                )
                tracker.start()
                # 启动时是否自动开启跟踪
                if tk_cfg.get("autostart", False):
                    tracker.enable(True)
        except Exception as e:
            logger.warning(f"摄像头初始化失败: {e}")
            camera = None
            tracker = None

    # 5. LLM + 对话编排 (传入摄像头以支持视觉问答)
    llm = None
    try:
        llm = create_provider(cfg.get("llm", {}))
        if llm:
            logger.info(f"LLM 已启用: {type(llm).__name__}")
    except Exception as e:
        logger.warning(f"LLM 初始化失败: {e}")

    dialogue = DialogueOrchestrator(
        llm=llm, servo=servo, face=face, voice=voice, camera=camera,
    )

    # 6. 优雅退出
    def handle_exit(signum, frame):
        logger.info(f"收到信号 {signum},清理资源...")
        if tracker: tracker.cleanup()
        if camera:  camera.cleanup()
        servo.cleanup()
        face.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    # 7. Web 服务
    app, socketio = create_app(
        servo=servo, face=face, voice=voice,
        dialogue=dialogue, camera=camera, tracker=tracker,
        config=cfg,
    )
    run_server(
        app, socketio,
        host=cfg["web"]["host"],
        port=cfg["web"]["port"],
    )


if __name__ == "__main__":
    main()
