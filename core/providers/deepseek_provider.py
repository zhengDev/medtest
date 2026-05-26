from __future__ import annotations
import json
from typing import Iterator
import requests
from config.settings import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from core.providers.base_llm import BaseLLMProvider


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek API 实现（OpenAI 兼容格式）。"""

    def __init__(self):
        if not DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY 未配置，请在 config/settings.py 中填入")
        self.headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }

    def generate_stream(self, prompt: str) -> Iterator[str]:
        url = f"{DEEPSEEK_BASE_URL}/chat/completions"
        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }
        with requests.post(url, headers=self.headers, json=payload, stream=True, timeout=60) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line or line == b"data: [DONE]":
                    continue
                raw = line.decode("utf-8").removeprefix("data: ")
                chunk = json.loads(raw)
                delta = chunk["choices"][0]["delta"].get("content", "")
                if delta:
                    yield delta

    def health_check(self) -> bool:
        try:
            resp = requests.get(
                f"{DEEPSEEK_BASE_URL}/models",
                headers=self.headers,
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            return False
