"""单元测试：question_bank 模块（SmartParser + SQLiteStore + PipelineV2）。
不依赖网络、ChromaDB 或 Embedding 模型。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
import pytest
from core.question_bank.models import (
    Question, Q_TYPE_SINGLE, Q_TYPE_MULTI, Q_TYPE_JUDGE, Q_TYPE_FILL, Q_TYPE_ESSAY,
)
from core.question_bank.sqlite_store import QuestionStore
from core.question_bank.smart_parser import SmartQuestionParser


# ── 辅助 ────────────────────────────────────────────────────

def _make_store(tmp_path) -> QuestionStore:
    return QuestionStore(str(tmp_path / "test.db"))


def _q(stem="题干", q_type=Q_TYPE_SINGLE, options=None, answer="A") -> Question:
    from hashlib import md5
    return Question(
        id=None, paper_id=None,
        q_hash=md5(stem.encode()).hexdigest(),
        q_type=q_type,
        stem=stem,
        options=options or {"A": "选项A", "B": "选项B"},
        answer=answer,
    )


# ── SmartQuestionParser ──────────────────────────────────────

class TestSmartQuestionParser:
    PARSER = SmartQuestionParser()

    SINGLE_CHOICE_TEXT = """
1. 左心室壁比右心室壁厚，这是因为：
A. 左心室负责体循环，压力更大
B. 左心室负责肺循环，压力更大
C. 左右心室壁厚度相同
D. 右心室壁更厚
答案：A
解析：左心室需要泵血至全身。
"""

    JUDGE_TEXT = """
心脏位于胸腔中纵隔内，左右各有一心房和一心室，共4个腔室。
A. 正确
B. 错误
答案：A
解析：心脏有四个腔室。
"""

    MULTI_CHOICE_TEXT = """
1. 关于高血压的治疗，下列正确的有：
A. 生活方式干预
B. 药物治疗
C. 手术治疗（一线）
D. 低盐饮食
答案：AB
解析：一般不需手术治疗。
"""

    FILL_TEXT = """
1. 高血压的诊断标准是收缩压≥____mmHg。
答案：140
"""

    SAMPLE_FIXTURE = """
心脏位于胸腔中纵隔内，左右各有一心房和一心室，共4个腔室。
A. 正确
B. 错误
答案：A
解析：心脏位于胸腔纵隔内，由左心房、左心室、右心房、右心室四个腔室组成。

左心室壁比右心室壁厚，这是因为：
A. 左心室负责体循环，压力更大
B. 左心室负责肺循环，压力更大
C. 左右心室壁厚度相同
D. 右心室壁更厚
答案：A
解析：左心室需要泵血至全身（体循环），压力约为右心室的5-6倍，因此壁更厚。
"""

    def test_parse_single_choice(self):
        qs = self.PARSER.parse_text(self.SINGLE_CHOICE_TEXT)
        assert len(qs) == 1
        q = qs[0]
        assert q.q_type == Q_TYPE_SINGLE
        assert "A" in q.options
        assert q.answer == "A"
        assert q.explanation != ""  # 解析已提取

    def test_parse_judge_question(self):
        qs = self.PARSER.parse_text(self.JUDGE_TEXT)
        assert len(qs) == 1
        q = qs[0]
        assert q.q_type == Q_TYPE_JUDGE
        assert q.answer == "T"

    def test_parse_multi_choice(self):
        qs = self.PARSER.parse_text(self.MULTI_CHOICE_TEXT)
        assert len(qs) == 1
        q = qs[0]
        assert q.q_type == Q_TYPE_MULTI
        assert q.answer == "AB"

    def test_parse_fill_blank(self):
        qs = self.PARSER.parse_text(self.FILL_TEXT)
        assert len(qs) == 1
        q = qs[0]
        assert q.q_type == Q_TYPE_FILL
        assert q.answer == "140"

    def test_parse_sample_fixture(self):
        qs = self.PARSER.parse_text(self.SAMPLE_FIXTURE)
        assert len(qs) == 2
        types = {q.q_type for q in qs}
        assert Q_TYPE_JUDGE in types or Q_TYPE_SINGLE in types

    def test_empty_text_returns_empty(self):
        assert self.PARSER.parse_text("") == []
        assert self.PARSER.parse_text("   \n  ") == []

    def test_normalize_answer_multi_sorts(self):
        from core.question_bank.smart_parser import _normalize_answer
        assert _normalize_answer("BA", Q_TYPE_MULTI) == "AB"
        assert _normalize_answer("CAB", Q_TYPE_MULTI) == "ABC"

    def test_normalize_answer_judge(self):
        from core.question_bank.smart_parser import _normalize_answer
        assert _normalize_answer("√", Q_TYPE_JUDGE) == "T"
        assert _normalize_answer("×", Q_TYPE_JUDGE) == "F"
        assert _normalize_answer("正确", Q_TYPE_JUDGE) == "T"
        assert _normalize_answer("错误", Q_TYPE_JUDGE) == "F"

    def test_duplicate_hash(self):
        text = self.SINGLE_CHOICE_TEXT
        qs1 = self.PARSER.parse_text(text)
        qs2 = self.PARSER.parse_text(text)
        assert qs1[0].q_hash == qs2[0].q_hash

    def test_parse_csv_row(self):
        row = {
            "question": "心脏有几个腔",
            "options": "A.2个 B.4个 C.6个",
            "answer": "B",
            "subject": "解剖学",
        }
        q = self.PARSER.parse_csv_row(row)
        assert q is not None
        assert q.stem == "心脏有几个腔"
        assert q.answer == "B"
        assert q.subject == "解剖学"

    def test_parse_json_item_dict_options(self):
        item = {
            "question": "高血压诊断标准",
            "options": {"A": "130/80", "B": "140/90"},
            "answer": "B",
        }
        q = self.PARSER.parse_json_item(item)
        assert q is not None
        assert q.options["B"] == "140/90"
        assert q.answer == "B"


# ── QuestionStore ────────────────────────────────────────────

class TestQuestionStore:

    def test_init_creates_tables(self, tmp_path):
        store = _make_store(tmp_path)
        # 能正常列出（空列表）
        assert store.list_papers() == []
        assert store.count_questions() == 0

    def test_add_questions_idempotent(self, tmp_path):
        store = _make_store(tmp_path)
        pid = store.create_paper("试卷1", "test.txt")
        q = _q("题目一")
        ins1, sk1 = store.add_questions([q], pid)
        ins2, sk2 = store.add_questions([q], pid)
        assert ins1 == 1
        assert sk2 == 1  # 第二次跳过
        assert store.count_questions() == 1

    def test_list_by_paper(self, tmp_path):
        store = _make_store(tmp_path)
        pid1 = store.create_paper("试卷A", "a.txt")
        pid2 = store.create_paper("试卷B", "b.txt")
        store.add_questions([_q("A的题目")], pid1)
        store.add_questions([_q("B的题目")], pid2)
        qs = store.list_questions(paper_id=pid1)
        assert len(qs) == 1
        assert qs[0].stem == "A的题目"

    def test_list_by_type(self, tmp_path):
        store = _make_store(tmp_path)
        pid = store.create_paper("试卷", "test.txt")
        store.add_questions([
            _q("选择题题干", Q_TYPE_SINGLE),
            _q("判断题题干", Q_TYPE_JUDGE, options={}, answer="T"),
        ], pid)
        singles = store.list_questions(q_type=Q_TYPE_SINGLE)
        judges = store.list_questions(q_type=Q_TYPE_JUDGE)
        assert len(singles) == 1
        assert len(judges) == 1

    def test_delete_paper_cascades(self, tmp_path):
        store = _make_store(tmp_path)
        pid = store.create_paper("试卷", "test.txt")
        store.add_questions([_q("题目A"), _q("题目B")], pid)
        assert store.count_questions() == 2
        store.delete_paper(pid)
        assert store.count_questions() == 0
        assert store.list_papers() == []

    def test_get_random_questions(self, tmp_path):
        store = _make_store(tmp_path)
        pid = store.create_paper("试卷", "test.txt")
        qs = [_q(f"题目{i}") for i in range(10)]
        store.add_questions(qs, pid)
        sample = store.get_random_questions(5)
        assert len(sample) == 5

    def test_group_lifecycle(self, tmp_path):
        store = _make_store(tmp_path)
        pid = store.create_paper("试卷", "test.txt")
        store.add_questions([_q("题目A"), _q("题目B"), _q("题目C")], pid)
        all_qs = store.list_questions()
        q_ids = [q.id for q in all_qs[:2]]

        gid = store.create_group("错题本")
        store.add_to_group(q_ids, gid)
        groups = store.list_groups()
        assert len(groups) == 1
        assert groups[0]["question_count"] == 2

        qs_in_group = store.list_questions(group_id=gid)
        assert len(qs_in_group) == 2

        store.remove_from_group([q_ids[0]], gid)
        assert store.count_questions(group_id=gid) == 1

        store.delete_group(gid)
        assert store.list_groups() == []

    def test_practice_session_flow(self, tmp_path):
        store = _make_store(tmp_path)
        pid = store.create_paper("试卷", "test.txt")
        store.add_questions([_q("题目A"), _q("题目B")], pid)
        all_qs = store.list_questions()

        sid = store.create_session("paper", pid, total=2)
        assert sid > 0

        store.add_record(sid, all_qs[0].id, "A", True)
        store.add_record(sid, all_qs[1].id, "B", False)

        store.complete_session(sid, correct=1)
        sessions = store.list_sessions()
        assert sessions[0].correct == 1
        assert sessions[0].status == "completed"

        detail = store.get_session_detail(sid)
        assert len(detail) == 2


# ── PipelineV2 ───────────────────────────────────────────────

class TestPipelineV2:

    def _run_import(self, tmp_path, content: str, suffix: str = ".txt") -> tuple[int, int]:
        import importlib
        from config import settings as s
        s.QUESTION_DB_PATH = str(tmp_path / "q.db")

        # 重置 pipeline 的单例 store
        import core.pipeline.question_pipeline_v2 as pv2
        pv2._store = None

        f = tmp_path / f"test{suffix}"
        f.write_text(content, encoding="utf-8")
        return pv2.import_questions_v2(f)

    def test_import_txt(self, tmp_path):
        content = """
1. 心脏有四个腔
A. 正确
B. 错误
答案：A

2. 肺有两叶
A. 正确
B. 错误
答案：B
"""
        ins, sk = self._run_import(tmp_path, content, ".txt")
        assert ins == 2

    def test_import_csv(self, tmp_path):
        content = "question,options,answer,subject\n心脏左心室壁的特点,A.最薄 B.最厚,B,解剖学\n"
        ins, sk = self._run_import(tmp_path, content, ".csv")
        assert ins == 1

    def test_import_json(self, tmp_path):
        data = [
            {"question": "高血压诊断标准", "options": {"A": "130/80", "B": "140/90"}, "answer": "B"},
        ]
        ins, sk = self._run_import(
            tmp_path,
            json.dumps(data, ensure_ascii=False),
            ".json",
        )
        assert ins == 1

    def test_import_idempotent(self, tmp_path):
        content = "question,answer\n高血压诊断,140/90\n"
        ins1, _ = self._run_import(tmp_path, content, ".csv")

        # 重用同一个 db，再次导入
        from config import settings as s
        from core.pipeline import question_pipeline_v2 as pv2
        pv2._store = None
        f = tmp_path / "test.csv"
        ins2, sk2 = pv2.import_questions_v2(f)
        assert ins2 == 0
        assert sk2 == 1
