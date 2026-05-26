from __future__ import annotations

# Rocky Linux / RHEL 9 自带 sqlite3 3.34.x，chromadb 需要 3.35+
# pysqlite3-binary 内置高版本 sqlite3，此处替换系统模块
try:
    __import__("pysqlite3")
    import sys
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

import chromadb
from config.settings import CHROMA_PERSIST_DIR
from core.vector_store.base_store import BaseVectorStore, Document, SearchResult


class ChromaStore(BaseVectorStore):
    """ChromaDB 嵌入式实现，数据持久化到磁盘。使用 0.4.x PersistentClient API。"""

    def __init__(self, collection_name: str, persist_dir: str = CHROMA_PERSIST_DIR):
        client = chromadb.PersistentClient(path=persist_dir)
        self._collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add(self, documents: list[Document], vectors: list[list[float]]) -> None:
        if not documents:
            return
        # 始终把 id 写入 metadata，方便 search 时回读；同时保证 metadata 非空
        metadatas = [{**d.metadata, "id": d.id} for d in documents]
        self._collection.upsert(
            ids=[d.id for d in documents],
            documents=[d.text for d in documents],
            embeddings=vectors,
            metadatas=metadatas,
        )

    def search(self, query_vector: list[float], top_k: int, score_threshold: float = 0.0) -> list[SearchResult]:
        count = self._collection.count()
        if count == 0:
            return []
        results = self._collection.query(
            query_embeddings=[query_vector],
            n_results=min(top_k, count),
            include=["documents", "metadatas", "distances"],
        )
        output = []
        for doc_id, doc_text, meta, distance in zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # ChromaDB cosine distance: 0=完全相同, 2=完全相反，转换为相似度
            score = 1.0 - distance / 2.0
            if score >= score_threshold:
                doc = Document(id=doc_id, text=doc_text, metadata=meta)
                output.append(SearchResult(document=doc, score=score))
        return output

    def delete(self, doc_id: str) -> None:
        self._collection.delete(ids=[doc_id])

    def count(self) -> int:
        return self._collection.count()

    def clear(self) -> None:
        self._collection.delete(ids=self._collection.get()["ids"])
