"""
集成测试：题库导入 + 检索完整流程。
需要 Embedding 模型已下载，运行前确保内存充足。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
import json
import tempfile
from core.pipeline.question_pipeline import import_questions, search_questions


@pytest.fixture(autouse=True)
def patch_chroma_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("config.settings.CHROMA_PERSIST_DIR", str(tmp_path / "chroma"))
    # 重置 store 单例（如有缓存）
    import importlib
    import core.vector_store
    importlib.reload(core.vector_store)


def _make_txt_file(tmp_path: Path, questions: list[str]) -> Path:
    f = tmp_path / "questions.txt"
    f.write_text("\n\n".join(questions), encoding="utf-8")
    return f


def _make_csv_file(tmp_path: Path) -> Path:
    f = tmp_path / "questions.csv"
    f.write_text(
        "question,options,answer,subject\n"
        "心脏左心室壁的特点,A.最薄 B.最厚 C.与右心室等厚,B,解剖学\n"
        "肺循环起始于哪里,A.左心室 B.右心室 C.左心房,B,解剖学\n",
        encoding="utf-8",
    )
    return f


def _make_json_file(tmp_path: Path) -> Path:
    f = tmp_path / "questions.json"
    data = [
        {"question": "高血压诊断标准是什么", "options": {"A": "130/80", "B": "140/90", "C": "150/100"}, "answer": "B"},
        {"question": "正常成人收缩压范围", "options": {"A": "90-140mmHg", "B": "60-90mmHg"}, "answer": "A"},
    ]
    f.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return f


class TestImportQuestions:
    def test_import_txt(self, tmp_path):
        questions = ["心脏有四个腔\nA.正确 B.错误", "肺有两叶\nA.正确 B.错误"]
        f = _make_txt_file(tmp_path, questions)
        count = import_questions(f)
        assert count == 2

    def test_import_csv(self, tmp_path):
        f = _make_csv_file(tmp_path)
        count = import_questions(f)
        assert count == 2

    def test_import_json(self, tmp_path):
        f = _make_json_file(tmp_path)
        count = import_questions(f)
        assert count == 2

    def test_idempotent_import(self, tmp_path):
        questions = ["心脏有四个腔\nA.正确 B.错误"]
        f = _make_txt_file(tmp_path, questions)
        count1 = import_questions(f)
        count2 = import_questions(f)
        assert count1 == count2  # 重复导入不增加数量


class TestSearchQuestions:
    def test_search_returns_relevant_results(self, tmp_path):
        questions = [
            "心脏左心室壁最厚，因为需要泵血至全身\nA.正确 B.错误",
            "肺循环是体循环的一部分\nA.正确 B.错误",
            "高血压诊断标准为140/90mmHg以上\nA.正确 B.错误",
        ]
        f = _make_txt_file(tmp_path, questions)
        import_questions(f)

        results = search_questions("左心室壁厚度", top_k=3)
        assert len(results) >= 1
        # 第一条结果应与心脏/左心室相关
        assert "心脏" in results[0].document.text or "左心室" in results[0].document.text

    def test_search_score_between_0_and_1(self, tmp_path):
        questions = ["心脏解剖结构\nA.正确 B.错误"]
        f = _make_txt_file(tmp_path, questions)
        import_questions(f)
        results = search_questions("心脏", top_k=1)
        if results:
            assert 0.0 <= results[0].score <= 1.0

    def test_search_empty_store_returns_empty(self, tmp_path):
        results = search_questions("任意查询", top_k=5)
        assert results == []
