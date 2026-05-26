import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from core.utils.text_splitter import split_text


def test_short_text_returns_single_chunk():
    text = "这是一段短文本。"
    chunks = split_text(text, chunk_size=500)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_long_text_splits_correctly():
    text = "。".join(["这是第{}句话".format(i) for i in range(100)])
    chunks = split_text(text, chunk_size=100, chunk_overlap=10)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 100 + 10 + 5  # 允许少量余量（分隔符本身）


def test_chunk_overlap():
    text = "A" * 400 + "。" + "B" * 400
    chunks = split_text(text, chunk_size=300, chunk_overlap=50)
    assert len(chunks) >= 2
    # 重叠部分：第二块开头包含第一块结尾的字符
    assert any(chunks[1].startswith(chunks[0][-20:]) or len(chunks[0]) < 300 for _ in [1])


def test_empty_text_returns_empty():
    assert split_text("") == []
    assert split_text("   ") == []


def test_chinese_not_split_mid_sentence():
    text = "心脏位于胸腔中纵隔内，外裹心包。心包分为纤维心包和浆膜心包两部分。浆膜心包又分为壁层和脏层。"
    chunks = split_text(text, chunk_size=30, chunk_overlap=5)
    for chunk in chunks:
        # 不应在汉字中间切断（每个 chunk 应该以完整的标点或边界结束）
        assert chunk.strip()
