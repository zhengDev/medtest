from __future__ import annotations
import json
from typing import Iterator
import requests
from config.settings import ZHIPU_API_KEY, ZHIPU_MODEL
from core.providers.base_llm import BaseLLMProvider

_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"


class ZhipuProvider(BaseLLMProvider):
    """智谱 GLM 实现（GLM-4-Flash 完全免费）。"""

    def __init__(self):
        if not ZHIPU_API_KEY:
            raise ValueError("ZHIPU_API_KEY 未配置，请在 config/settings.py 中填入")
        self.headers = {
            "Authorization": f"Bearer {ZHIPU_API_KEY}",
            "Content-Type": "application/json",
        }

    def generate_stream(self, prompt: str) -> Iterator[str]:
        url = f"{_BASE_URL}/chat/completions"
        payload = {
            "model": ZHIPU_MODEL,
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
            resp = requests.get(f"{_BASE_URL}/models", headers=self.headers, timeout=5)
            return resp.status_code == 200
        except Exception:
            return False
