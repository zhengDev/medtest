from pathlib import Path
from docx import Document
from core.parsers.base_parser import BaseParser, register_parser


@register_parser
class DocxParser(BaseParser):
    supported_extensions = [".docx"]

    def parse(self, file_path: Path) -> str:
        doc = Document(str(file_path))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
