from __future__ import annotations
from sentence_transformers import SentenceTransformer
from config.settings import EMBEDDING_MODEL, EMBEDDING_DEVICE, EMBEDDING_BATCH_SIZE
from core.providers.base_embedder import BaseEmbedder


class E5Embedder(BaseEmbedder):
    """multilingual-e5-small 实现。E5 系列需要在文本前加前缀以区分查询/文档。"""

    _QUERY_PREFIX = "query: "
    _PASSAGE_PREFIX = "passage: "
    _DIMENSION = 384
    _instance: "E5Embedder | None" = None

    def __init__(self, model: SentenceTransformer):
        self._model = model

    @classmethod
    def load(cls) -> "E5Embedder":
        """单例加载，进程内只初始化一次，兼容 pytest 和 Streamlit 环境。"""
        if cls._instance is None:
            model = SentenceTransformer(EMBEDDING_MODEL, device=EMBEDDING_DEVICE)
            cls._instance = cls(model)
        return cls._instance

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        prefixed = [self._PASSAGE_PREFIX + t for t in texts]
        vectors = self._model.encode(
            prefixed,
            batch_size=EMBEDDING_BATCH_SIZE,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        vector = self._model.encode(
            self._QUERY_PREFIX + text,
            normalize_embeddings=True,
        )
        return vector.tolist()

    @property
    def dimension(self) -> int:
        return self._DIMENSION
