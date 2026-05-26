from config.settings import LLM_PROVIDER, EMBEDDING_PROVIDER
from core.providers.base_llm import BaseLLMProvider
from core.providers.base_embedder import BaseEmbedder


def get_llm_provider() -> BaseLLMProvider:
    """根据 settings.LLM_PROVIDER 返回对应实现，切换时只改配置。"""
    if LLM_PROVIDER == "ollama":
        from core.providers.ollama_provider import OllamaProvider
        return OllamaProvider()
    if LLM_PROVIDER == "deepseek":
        from core.providers.deepseek_provider import DeepSeekProvider
        return DeepSeekProvider()
    if LLM_PROVIDER == "zhipu":
        from core.providers.zhipu_provider import ZhipuProvider
        return ZhipuProvider()
    raise ValueError(f"未知的 LLM_PROVIDER: {LLM_PROVIDER}，支持: ollama / deepseek / zhipu")


def get_embedder() -> BaseEmbedder:
    """根据 settings.EMBEDDING_PROVIDER 返回对应实现。"""
    if EMBEDDING_PROVIDER == "e5":
        from core.providers.e5_embedder import E5Embedder
        return E5Embedder.load()
    raise ValueError(f"未知的 EMBEDDING_PROVIDER: {EMBEDDING_PROVIDER}")
