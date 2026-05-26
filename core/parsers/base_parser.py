from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path

# 全局解析器注册表：扩展名 → 解析器类
_REGISTRY: dict[str, type["BaseParser"]] = {}


def register_parser(cls: type["BaseParser"]) -> type["BaseParser"]:
    """装饰器：将解析器自动注册到全局注册表。"""
    for ext in cls.supported_extensions:
        _REGISTRY[ext.lower()] = cls
    return cls


def get_parser(file_path: Path) -> "BaseParser":
    """根据文件扩展名查找解析器，未知格式抛 ValueError。"""
    ext = file_path.suffix.lower()
    cls = _REGISTRY.get(ext)
    if cls is None:
        supported = ", ".join(sorted(_REGISTRY.keys()))
        raise ValueError(f"不支持的文件格式 '{ext}'，当前支持: {supported}")
    return cls()


class BaseParser(ABC):
    """文档解析器抽象接口。新增格式只需继承此类并加 @register_parser 装饰器。"""

    supported_extensions: list[str] = []

    @abstractmethod
    def parse(self, file_path: Path) -> str:
        """解析文件，返回纯文本字符串。"""
