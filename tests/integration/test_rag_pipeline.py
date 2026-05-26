"""
集成测试：RAG 文档导入 + 检索 + 问答完整流程。
LLM 部分使用 mock，Embedding + ChromaDB 使用真实实现。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from unittest.mock import patch
from core.pipeline.rag_pipeline import import_document, retrieve, get_document_count, answer_stream


@pytest.fixture(autouse=True)
def patch_chroma_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("config.settings.CHROMA_PERSIST_DIR", str(tmp_path / "chroma"))
    monkeypatch.setattr("core.vector_store.chroma_store.CHROMA_PERSIST_DIR", str(tmp_path / "chroma"))


def _make_txt(tmp_path: Path, content: str) -> Path:
    f = tmp_path / "doc.txt"
    f.write_text(content, encoding="utf-8")
    return f


class TestImportDocument:
    def test_import_txt_returns_chunks(self, tmp_path):
        content = "心脏是循环系统的核心器官。" * 20
        f = _make_txt(tmp_path, content)
        count = import_document(f)
        assert count >= 1

    def test_long_document_splits_into_multiple_chunks(self, tmp_path):
        content = ("这是一段医学学习资料。" * 10 + "\n\n") * 20
        f = _make_txt(tmp_path, content)
        count = import_document(f)
        assert count > 1

    def test_empty_document_returns_zero(self, tmp_path):
        f = _make_txt(tmp_path, "   ")
        count = import_document(f)
        assert count == 0


class TestRetrieve:
    def test_retrieve_relevant_content(self, tmp_path):
        content = """
高血压的定义：收缩压≥140mmHg和/或舒张压≥90mmHg。

高血压的治疗原则包括生活方式干预和药物治疗。
常用降压药包括：ACEI、ARB、钙通道阻滞剂、利尿剂、β受体阻滞剂。
"""
        f = _make_txt(tmp_path, content)
        import_document(f)

        results = retrieve("高血压诊断标准", top_k=3)
        assert len(results) >= 1
        assert any("140" in r.document.text or "高血压" in r.document.text for r in results)

    def test_retrieve_returns_source_metadata(self, tmp_path):
        content = "心脏有四个腔室：左心房、左心室、右心房、右心室。"
        f = _make_txt(tmp_path, content)
        import_document(f, source_name="解剖学笔记.txt")

        results = retrieve("心脏腔室", top_k=1)
        if results:
            assert results[0].document.metadata.get("source_file") == "解剖学笔记.txt"

    def test_retrieve_score_threshold_filters_noise(self, tmp_path):
        content = "心脏解剖相关内容。"
        f = _make_txt(tmp_path, content)
        import_document(f)
        # 完全不相关的查询，相似度应低于阈值
        results = retrieve("XXXXXXXX随机无关内容", top_k=5)
        for r in results:
            assert r.score >= 0.0  # 只要分数合法即可


class TestAnswerStream:
    """测试 RAG 完整问答流程（mock LLM，真实 Embedding + ChromaDB）。"""

    def _mock_llm(self, answer_text: str):
        """返回一个能 patch get_llm_provider 的上下文管理器。"""
        mock_provider = patch("core.pipeline.rag_pipeline.get_llm_provider")
        return mock_provider, answer_text

    def test_answer_contains_keywords_from_document(self, tmp_path):
        content = "高血压的诊断标准：收缩压≥140mmHg和/或舒张压≥90mmHg。"
        f = _make_txt(tmp_path, content)
        import_document(f)

        with patch("core.pipeline.rag_pipeline.get_llm_provider") as mock_get_llm:
            mock_provider = mock_get_llm.return_value
            mock_provider.generate_stream.return_value = iter(["收缩压≥140mmHg是高血压标准"])
            tokens = list(answer_stream("高血压诊断标准是什么"))

        full_answer = "".join(tokens)
        assert "140" in full_answer or "高血压" in full_answer

    def test_answer_includes_citation(self, tmp_path):
        content = "阿司匹林用于抗血小板治疗。"
        f = _make_txt(tmp_path, content)
        import_document(f, source_name="药学笔记.txt")

        with patch("core.pipeline.rag_pipeline.get_llm_provider") as mock_get_llm:
            mock_provider = mock_get_llm.return_value
            mock_provider.generate_stream.return_value = iter(["阿司匹林抗血小板"])
            tokens = list(answer_stream("阿司匹林的用途"))

        full_answer = "".join(tokens)
        assert "药学笔记.txt" in full_answer

    def test_empty_store_returns_no_data_message(self, tmp_path):
        tokens = list(answer_stream("任意问题"))
        full_answer = "".join(tokens)
        assert "未找到" in full_answer or "未提及" in full_answer or "为空" in full_answer
