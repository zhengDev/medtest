from abc import ABC, abstractmethod
from typing import Iterator


class BaseLLMProvider(ABC):
    """LLM 提供者抽象接口。切换 LLM 只需新建子类并修改 settings.LLM_PROVIDER。"""

    @abstractmethod
    def generate_stream(self, prompt: str) -> Iterator[str]:
        """流式生成，逐 token yield 字符串片段。"""

    @abstractmethod
    def health_check(self) -> bool:
        """检查服务是否可用，返回 True/False。"""
