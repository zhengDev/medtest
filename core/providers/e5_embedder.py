from __future__ import annotations
import streamlit as st
from sentence_transformers import SentenceTransformer
from config.settings import EMBEDDING_MODEL, EMBEDDING_DEVICE, EMBEDDING_BATCH_SIZE
from core.providers.base_embedder import BaseEmbedder


class E5Embedder(BaseEmbedder):
    """multilingual-e5-small 实现。E5 系列需要在文本前加前缀以区分查询/文档。"""

    _QUERY_PREFIX = "query: "
    _PASSAGE_PREFIX = "passage: "
    _DIMENSION = 384

    def __init__(self, model: SentenceTransformer):
        self._model = model

    @classmethod
    @st.cache_resource
    def load(cls) -> "E5Embedder":
        """单例加载，配合 @st.cache_resource 防止重复占用内存。"""
        model = SentenceTransformer(EMBEDDING_MODEL, device=EMBEDDING_DEVICE)
        return cls(model)

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
