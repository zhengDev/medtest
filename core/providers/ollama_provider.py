from __future__ import annotations
import json
from typing import Iterator
import requests
from config.settings import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT
from core.providers.base_llm import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    """Ollama 本地推理实现，使用 HTTP 流式 API。"""

    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_MODEL):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate_stream(self, prompt: str) -> Iterator[str]:
        url = f"{self.base_url}/api/generate"
        payload = {"model": self.model, "prompt": prompt, "stream": True}
        with requests.post(url, json=payload, stream=True, timeout=OLLAMA_TIMEOUT) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    chunk = json.loads(line)
                    token = chunk.get("response", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break

    def health_check(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False
