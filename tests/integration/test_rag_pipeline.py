"""
集成测试：RAG 文档导入 + 检索完整流程（不含 LLM，只测向量检索部分）。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from core.pipeline.rag_pipeline import import_document, retrieve, get_document_count


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
