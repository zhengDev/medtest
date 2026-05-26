from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Document:
    id: str
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass
class SearchResult:
    document: Document
    score: float           # 相似度分数，越高越相似 (0~1)


class BaseVectorStore(ABC):
    """向量库抽象接口。切换向量库只需新建子类并修改 settings.VECTOR_STORE_PROVIDER。"""

    @abstractmethod
    def add(self, documents: list[Document], vectors: list[list[float]]) -> None:
        """批量插入文档及其向量。"""

    @abstractmethod
    def search(self, query_vector: list[float], top_k: int, score_threshold: float = 0.0) -> list[SearchResult]:
        """向量检索，返回相似度高于阈值的结果列表。"""

    @abstractmethod
    def delete(self, doc_id: str) -> None:
        """按 ID 删除文档。"""

    @abstractmethod
    def count(self) -> int:
        """返回当前存储的文档数量。"""

    @abstractmethod
    def clear(self) -> None:
        """清空所有数据（危险操作，用于测试）。"""
