# 导入所有解析器以触发 @register_parser 注册
from core.parsers import pdf_parser, docx_parser, txt_parser  # noqa: F401
from core.parsers.base_parser import get_parser  # noqa: F401
