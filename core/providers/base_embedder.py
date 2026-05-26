from abc import ABC, abstractmethod


class BaseEmbedder(ABC):
    """Embedding 提供者抽象接口。切换模型只需新建子类并修改 settings.EMBEDDING_PROVIDER。"""

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量向量化文档片段，返回向量列表。"""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """向量化单条查询，子类可在此添加查询专用前缀。"""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """向量维度，用于初始化向量库。"""
