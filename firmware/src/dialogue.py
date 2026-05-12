# -*- coding: utf-8 -*-
"""
对话编排器 (Dialogue Orchestrator)
==================================
把 LLM 返回的结构化结果 (say + expression + motion) 拆解为三路并发执行:
  1. 表情切换
  2. 头部动作 (点头/摇头)
  3. TTS 语音
所有动作非阻塞,通过线程并发,保证用户体感"自然"。
"""
import logging
import threading
from typing import Optional

from .llm_provider import BaseLLMProvider, LLMResponse

logger = logging.getLogger("dialogue")


class DialogueOrchestrator:
    def __init__(self, llm: Optional[BaseLLMProvider],
                 servo, face, voice):
        self.llm = llm
        self.servo = servo
        self.face = face
        self.voice = voice
        self._lock = threading.Lock()  # 同一时刻只处理一次对话
        self._last_response: Optional[LLMResponse] = None

    @property
    def available(self) -> bool:
        return self.llm is not None

    def chat(self, user_text: str) -> dict:
        """
        同步入口:输入用户话,触发完整反应。
        返回 LLM 的结构化结果(供 Web 端显示)。
        """
        if not self.llm:
            return {"error": "LLM 未启用"}

        with self._lock:
            logger.info(f"用户: {user_text}")
            resp = self.llm.chat(user_text)
            self._last_response = resp
            logger.info(f"LLM: say='{resp.say}' expr={resp.expression} motion={resp.motion}")
            self._execute(resp)
            return resp.to_dict()

    def _execute(self, resp: LLMResponse):
        """三路并发: 表情立刻切换, 动作和 TTS 并行"""
        # 1) 表情 (同步, 立刻)
        if resp.expression and resp.expression != "none":
            try:
                self.face.show(resp.expression)
            except Exception as e:
                logger.error(f"表情切换失败: {e}")

        # 2) 动作 (异步线程)
        if resp.motion and resp.motion not in ("none", ""):
            threading.Thread(
                target=self._do_motion, args=(resp.motion,), daemon=True
            ).start()

        # 3) TTS (异步)
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
