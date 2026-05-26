from config.settings import VECTOR_STORE_PROVIDER
from core.vector_store.base_store import BaseVectorStore


def get_store(collection_name: str) -> BaseVectorStore:
    """根据 settings.VECTOR_STORE_PROVIDER 返回对应实现。"""
    if VECTOR_STORE_PROVIDER == "chroma":
        from core.vector_store.chroma_store import ChromaStore
        return ChromaStore(collection_name)
    raise ValueError(f"未知的 VECTOR_STORE_PROVIDER: {VECTOR_STORE_PROVIDER}")
