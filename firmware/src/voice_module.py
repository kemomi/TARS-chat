'''
Author: fbee3157 fbee3157@outlook.com
Date: 2026-05-12 16:59:03
LastEditors: fbee3157 fbee3157@outlook.com
LastEditTime: 2026-05-12 18:03:40
FilePath: \TARS-chat\firmware\src\voice_module.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
# -*- coding: utf-8 -*-
"""
语音模块
- TTS: pyttsx3 (离线) / edge-tts (在线, 音质更好)
- STT: 占位接口, 可对接 Whisper / Vosk
"""
import logging
import threading
import subprocess
import shutil

logger = logging.getLogger("voice")


class VoiceModule:
    def __init__(self, tts_engine: str = "pyttsx3", lang: str = "zh"):
        self.tts_engine_name = tts_engine
        self.lang = lang
        self._engine = None
        self._lock = threading.Lock()
        self._init_engine()

    def _init_engine(self):
        if self.tts_engine_name == "pyttsx3":
            try:
                import pyttsx3
                self._engine = pyttsx3.init()
                self._engine.setProperty("rate", 170)
                # 选中文音色 (若可用)
                for v in self._engine.getProperty("voices"):
                    if "zh" in (v.id or "").lower() or "chinese" in (v.name or "").lower():
                        self._engine.setProperty("voice", v.id)
                        break
                logger.info("pyttsx3 TTS 初始化完成")
            except Exception as e:
                logger.error(f"pyttsx3 初始化失败: {e}")
                self._engine = None

        elif self.tts_engine_name == "edge-tts":
            if not shutil.which("edge-tts"):
                logger.error("edge-tts 未安装: pip install edge-tts")
            else:
                logger.info("使用 edge-tts (在线)")

    def speak(self, text: str, blocking: bool = False):
        if not text:
            return
        logger.info(f"[TTS] {text}")

        def _run():
            with self._lock:
                if self.tts_engine_name == "pyttsx3" and self._engine:
                    try:
                        self._engine.say(text)
                        self._engine.runAndWait()
                    except Exception as e:
                        logger.error(f"TTS 失败: {e}")
                elif self.tts_engine_name == "edge-tts":
                    self._edge_tts_speak(text)

        if blocking:
            _run()
        else:
            threading.Thread(target=_run, daemon=True).start()

    def _edge_tts_speak(self, text: str):
        """使用 edge-tts 生成 mp3 并通过 mpg123 播放"""
        voice = "zh-CN-XiaoxiaoNeural" if self.lang == "zh" else "en-US-AriaNeural"
        try:
            subprocess.run(
                ["edge-tts", "--voice", voice, "--text", text, "--write-media", "/tmp/tts.mp3"],
                check=True, timeout=20,
            )
            player = shutil.which("mpg123") or shutil.which("ffplay")
            if player:
                subprocess.run([player, "-q", "/tmp/tts.mp3"], check=False, timeout=30)
            else:
                logger.warning("未安装 mpg123 或 ffplay,无法播放音频")
        except Exception as e:
            logger.error(f"edge-tts 失败: {e}")