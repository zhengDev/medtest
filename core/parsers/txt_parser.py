from pathlib import Path
from core.parsers.base_parser import BaseParser, register_parser


@register_parser
class TxtParser(BaseParser):
    """处理 .txt 文件，自动检测 UTF-8 / GBK 编码。"""
    supported_extensions = [".txt"]

    def parse(self, file_path: Path) -> str:
        for encoding in ("utf-8", "gbk", "utf-8-sig"):
            try:
                return file_path.read_text(encoding=encoding)
            except (UnicodeDecodeError, ValueError):
                continue
        raise ValueError(f"无法解码文件 {file_path.name}，请确认编码为 UTF-8 或 GBK")
