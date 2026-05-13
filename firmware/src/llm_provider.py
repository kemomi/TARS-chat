# -*- coding: utf-8 -*-
"""
 # 🧠 LLM 抽象层 (OpenAI/Anthropic/Ollama)
==================
统一三种后端: OpenAI / Anthropic / Ollama
返回结构化结果: {text, action}
  action = {"expression": "happy", "motion": "nod", ...}  可选
"""
import abc
import json
import logging
import os
import re
from typing import Iterator, Optional

import requests

logger = logging.getLogger("llm")


# ---------------------------------------------------------------------------
# 系统提示词: 让 LLM 输出 JSON 结构,自带表情/动作意图
# ---------------------------------------------------------------------------
DEFAULT_SYSTEM_PROMPT = """你是 TARS-chat,一个圆滚滚的桌面机器人。你的性格活泼、好奇、有点话痨。
回答时必须严格输出 JSON,不要带任何代码块标记:
{
  "say": "你要说的话(简短,30字以内,口语化)",
  "expression": "happy | sad | angry | surprised | sleepy | neutral",
  "motion": "nod | shake | center | none"
}
表情和动作要匹配语义,例如同意时点头(nod)、否定时摇头(shake)。
"""


class LLMResponse:
    """LLM 返回结果的结构化封装"""
    def __init__(self, say: str = "", expression: str = "neutral",
                 motion: str = "none", raw: str = ""):
        self.say = say
        self.expression = expression
        self.motion = motion
        self.raw = raw

    def to_dict(self):
        return {"say": self.say, "expression": self.expression, "motion": self.motion}

    @classmethod
    def parse(cls, text: str) -> "LLMResponse":
        """从 LLM 原始输出尝试解析 JSON,失败则降级为纯文本"""
        # 兼容 ```json ... ``` 包裹
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.M)
        try:
            obj = json.loads(cleaned)
            return cls(
                say=obj.get("say", "").strip(),
                expression=obj.get("expression", "neutral"),
                motion=obj.get("motion", "none"),
                raw=text,
            )
        except json.JSONDecodeError:
            # 降级: 整段当作 say
            logger.warning(f"LLM 输出非 JSON,降级为纯文本: {text[:80]}")
            return cls(say=text.strip(), raw=text)


class BaseLLMProvider(abc.ABC):
    def __init__(self, system_prompt: str = DEFAULT_SYSTEM_PROMPT,
                 max_history: int = 10):
        self.system_prompt = system_prompt
        self.max_history = max_history
        self.history: list[dict] = []

    def _push_history(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        # 保留最近 N 轮 (一轮 = user + assistant)
        if len(self.history) > self.max_history * 2:
            self.history = self.history[-self.max_history * 2:]

    def reset(self):
        self.history.clear()

    @abc.abstractmethod
    def _chat(self, messages: list[dict]) -> str:
        ...

    def chat(self, user_text: str) -> LLMResponse:
        self._push_history("user", user_text)
        messages = [{"role": "system", "content": self.system_prompt}] + self.history
        try:
            raw = self._chat(messages)
            self._push_history("assistant", raw)
            return LLMResponse.parse(raw)
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return LLMResponse(say=f"我现在脑子有点短路: {e}", expression="sad")


# ---------------------------------------------------------------------------
# OpenAI / OpenAI-compatible
# ---------------------------------------------------------------------------
class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini",
                 base_url: str = "https://api.openai.com/v1", **kw):
        super().__init__(**kw)
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("OpenAI API key 未配置")
        self.model = model
        self.base_url = base_url.rstrip("/")

    def _chat(self, messages: list[dict]) -> str:
        r = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 200,
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# Anthropic Claude
# ---------------------------------------------------------------------------
class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001", **kw):
        super().__init__(**kw)
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not self.api_key:
            raise ValueError("Anthropic API key 未配置")
        self.model = model

    def _chat(self, messages: list[dict]) -> str:
        # Anthropic API 把 system 单独拆出来
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        msgs = [m for m in messages if m["role"] != "system"]

        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "system": system,
                "messages": msgs,
                "max_tokens": 300,
            },
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["content"][0]["text"]


# ---------------------------------------------------------------------------
# Ollama (本地)
# ---------------------------------------------------------------------------
class OllamaProvider(BaseLLMProvider):
    def __init__(self, model: str = "qwen2.5:3b",
                 base_url: str = "http://localhost:11434", **kw):
        super().__init__(**kw)
        self.model = model
        self.base_url = base_url.rstrip("/")

    def _chat(self, messages: list[dict]) -> str:
        r = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.7},
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["message"]["content"]


# ---------------------------------------------------------------------------
# 工厂
# ---------------------------------------------------------------------------
def create_provider(cfg: dict) -> Optional[BaseLLMProvider]:
    """根据 config['llm'] 创建对应的 Provider"""
    if not cfg.get("enabled", False):
        return None

    provider_name = cfg.get("provider", "ollama").lower()
    common = {
        "system_prompt": cfg.get("system_prompt", DEFAULT_SYSTEM_PROMPT),
        "max_history": cfg.get("max_history", 10),
    }

    if provider_name == "openai":
        return OpenAIProvider(
            api_key=cfg.get("api_key", ""),
            model=cfg.get("model", "gpt-4o-mini"),
            base_url=cfg.get("base_url", "https://api.openai.com/v1"),
            **common,
        )
    elif provider_name == "anthropic":
        return AnthropicProvider(
            api_key=cfg.get("api_key", ""),
            model=cfg.get("model", "claude-haiku-4-5-20251001"),
            **common,
        )
    elif provider_name == "ollama":
        return OllamaProvider(
            model=cfg.get("model", "qwen2.5:3b"),
            base_url=cfg.get("base_url", "http://localhost:11434"),
            **common,
        )
    else:
        raise ValueError(f"未知 LLM provider: {provider_name}")
