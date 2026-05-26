from pathlib import Path
import fitz  # PyMuPDF
from core.parsers.base_parser import BaseParser, register_parser


@register_parser
class PDFParser(BaseParser):
    supported_extensions = [".pdf"]

    def parse(self, file_path: Path) -> str:
        texts = []
        with fitz.open(str(file_path)) as doc:
            for page in doc:
                text = page.get_text("text")
                if text.strip():
                    texts.append(text.strip())
        return "\n\n".join(texts)
