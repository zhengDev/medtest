from __future__ import annotations
import chromadb
from chromadb.config import Settings
from config.settings import CHROMA_PERSIST_DIR
from core.vector_store.base_store import BaseVectorStore, Document, SearchResult


class ChromaStore(BaseVectorStore):
    """ChromaDB 嵌入式实现，数据持久化到磁盘。"""

    def __init__(self, collection_name: str):
        client = chromadb.Client(
            Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=CHROMA_PERSIST_DIR,
                anonymized_telemetry=False,
            )
        )
        self._collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add(self, documents: list[Document], vectors: list[list[float]]) -> None:
        if not documents:
            return
        self._collection.upsert(
            ids=[d.id for d in documents],
            documents=[d.text for d in documents],
            embeddings=vectors,
            metadatas=[d.metadata for d in documents],
        )

    def search(self, query_vector: list[float], top_k: int, score_threshold: float = 0.0) -> list[SearchResult]:
        results = self._collection.query(
            query_embeddings=[query_vector],
            n_results=min(top_k, max(self._collection.count(), 1)),
            include=["documents", "metadatas", "distances"],
        )
        output = []
        for doc_text, meta, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # ChromaDB cosine distance: 0=完全相同, 2=完全相反，转换为相似度
            score = 1.0 - distance / 2.0
            if score >= score_threshold:
                doc = Document(id=meta.get("id", ""), text=doc_text, metadata=meta)
                output.append(SearchResult(document=doc, score=score))
        return output

    def delete(self, doc_id: str) -> None:
        self._collection.delete(ids=[doc_id])

    def count(self) -> int:
        return self._collection.count()

    def clear(self) -> None:
        self._collection.delete(ids=self._collection.get()["ids"])
