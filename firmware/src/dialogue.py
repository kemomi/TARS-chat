# -*- coding: utf-8 -*-
"""
对话编排器 (Dialogue Orchestrator)
==================================
把 LLM 返回的结构化结果 (say + expression + motion) 拆解为三路并发执行:
  1. 表情切换
  2. 头部动作 (点头/摇头)
  3. TTS 语音
所有动作非阻塞,通过线程并发,保证用户体感"自然"。

视觉问答:
  用户提到 VISION_KEYWORDS 中任一关键词时,自动拍照传给 LLM
  (需要 LLM Provider 支持 vision: OpenAI gpt-4o / Anthropic Claude 都行)
"""
import logging
import threading
from typing import Optional

from .llm_provider import BaseLLMProvider, LLMResponse

logger = logging.getLogger("dialogue")

VISION_KEYWORDS = ("看到", "看看", "看一下", "看一眼", "你看", "瞧一眼",
                   "前面", "面前", "周围", "环境", "现在拍",
                   "what do you see", "look at", "describe")


class DialogueOrchestrator:
    def __init__(self, llm: Optional[BaseLLMProvider],
                 servo, face, voice, camera=None):
        self.llm = llm
        self.servo = servo
        self.face = face
        self.voice = voice
        self.camera = camera
        self._lock = threading.Lock()
        self._last_response: Optional[LLMResponse] = None

    @property
    def available(self) -> bool:
        return self.llm is not None

    @property
    def vision_available(self) -> bool:
        return self.camera is not None and self.llm is not None

    def chat(self, user_text: str, force_vision: bool = False) -> dict:
        """
        同步入口:输入用户话,触发完整反应。
        force_vision=True 强制拍照(用于 Web 端"拍一张并问"按钮)
        """
        if not self.llm:
            return {"error": "LLM 未启用"}

        with self._lock:
            logger.info(f"用户: {user_text}")

            # 自动判定是否需要视觉
            use_vision = force_vision or self._needs_vision(user_text)
            image_b64 = None
            if use_vision and self.camera:
                image_b64 = self.camera.snapshot_base64()
                if image_b64:
                    logger.info(f"已附带摄像头快照 ({len(image_b64)} chars base64)")

            resp = self.llm.chat(user_text, image_b64=image_b64)
            self._last_response = resp
            logger.info(f"LLM: say='{resp.say}' expr={resp.expression} motion={resp.motion}")
            self._execute(resp)
            return {**resp.to_dict(), "vision_used": image_b64 is not None}

    @staticmethod
    def _needs_vision(text: str) -> bool:
        low = text.lower()
        return any(k in low for k in VISION_KEYWORDS)

    def _execute(self, resp: LLMResponse):
        """三路并发: 表情立刻切换, 动作和 TTS 并行"""
        if resp.expression and resp.expression != "none":
            try:
                self.face.show(resp.expression)
            except Exception as e:
                logger.error(f"表情切换失败: {e}")

        if resp.motion and resp.motion not in ("none", ""):
            threading.Thread(
                target=self._do_motion, args=(resp.motion,), daemon=True
            ).start()

        if resp.say and self.voice:
            self.voice.speak(resp.say, blocking=False)

    def _do_motion(self, motion: str):
        try:
            if motion == "nod":
                self.servo.nod(2)
            elif motion == "shake":
                self.servo.shake(2)
            elif motion == "center":
                self.servo.center()
        except Exception as e:
            logger.error(f"动作失败 ({motion}): {e}")

    def reset(self):
        if self.llm:
            self.llm.reset()
        logger.info("对话历史已重置")

    @property
    def last(self) -> Optional[dict]:
        return self._last_response.to_dict() if self._last_response else None
