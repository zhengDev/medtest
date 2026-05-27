"""
题库 Pipeline v2：SQLite 存储，不依赖 ChromaDB 或 Embedding 模型。
"""
from __future__ import annotations
import csv
import json
from pathlib import Path
from typing import Optional

from config.settings import QUESTION_DB_PATH, QUESTIONS_COLLECTION
from core.question_bank.models import Question, PracticeSession
from core.question_bank.sqlite_store import QuestionStore
from core.question_bank.smart_parser import SmartQuestionParser
from core.parsers import get_parser

_store: Optional[QuestionStore] = None


def get_store() -> QuestionStore:
    global _store
    if _store is None:
        _store = QuestionStore(QUESTION_DB_PATH)
    return _store


def import_questions_v2(
    file_path: Path,
    source_name: str = "",
    paper_name: str = "",
) -> tuple[int, int]:
    """
    解析题库文件并写入 SQLite。
    返回 (新插入数, 跳过重复数)。
    """
    store = get_store()
    parser = SmartQuestionParser()
    name = paper_name or source_name or file_path.name
    suffix = file_path.suffix.lower()

    paper_id = store.create_paper(name=name, source_file=source_name or file_path.name)

    try:
        if suffix == ".csv":
            questions = _import_csv(file_path, paper_id, parser)
        elif suffix == ".json":
            questions = _import_json(file_path, paper_id, parser)
        else:
            # PDF / TXT：用文档解析器提取文本，再用 SmartQuestionParser 解析
            doc_parser = get_parser(file_path)
            raw_text = doc_parser.parse(file_path)
            questions = parser.parse_text(raw_text, paper_id=paper_id)
    except Exception as e:
        # 删除刚创建的空试卷记录
        store.delete_paper(paper_id)
        raise e

    if not questions:
        store.delete_paper(paper_id)
        return 0, 0

    inserted, skipped = store.add_questions(questions, paper_id)
    store.update_paper_count(paper_id, inserted)
    return inserted, skipped


def preview_questions(
    file_path: Path,
    source_name: str = "",
    max_count: int = 20,
) -> list[Question]:
    """解析文件并返回题目列表（不入库），用于导入前预览。"""
    parser = SmartQuestionParser()
    suffix = file_path.suffix.lower()

    if suffix == ".csv":
        questions = _import_csv(file_path, paper_id=None, parser=parser)
    elif suffix == ".json":
        questions = _import_json(file_path, paper_id=None, parser=parser)
    else:
        doc_parser = get_parser(file_path)
        raw_text = doc_parser.parse(file_path)
        questions = parser.parse_text(raw_text, paper_id=None)

    return questions[:max_count]


def _import_csv(
    file_path: Path,
    paper_id: Optional[int],
    parser: SmartQuestionParser,
) -> list[Question]:
    questions = []
    with open(file_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            q = parser.parse_csv_row(row, paper_id=paper_id)
            if q:
                questions.append(q)
    return questions


def _import_json(
    file_path: Path,
    paper_id: Optional[int],
    parser: SmartQuestionParser,
) -> list[Question]:
    data = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        data = [data]
    questions = []
    for item in data:
        q = parser.parse_json_item(item, paper_id=paper_id)
        if q:
            questions.append(q)
    return questions


# ── 查询和管理函数 ────────────────────────────────────────────

def list_papers() -> list[dict]:
    return get_store().list_papers()


def list_groups() -> list[dict]:
    return get_store().list_groups()


def get_questions(
    paper_id: Optional[int] = None,
    group_id: Optional[int] = None,
    q_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Question]:
    return get_store().list_questions(
        paper_id=paper_id, group_id=group_id,
        q_type=q_type, limit=limit, offset=offset,
    )


def get_question_count_v2(
    paper_id: Optional[int] = None,
    group_id: Optional[int] = None,
) -> int:
    return get_store().count_questions(paper_id=paper_id, group_id=group_id)


# ── 练习会话 ─────────────────────────────────────────────────

def start_practice_session(
    source_type: str,
    source_id: Optional[int],
    question_count: int,
    q_type: Optional[str] = None,
) -> tuple[int, list[Question]]:
    """创建会话并返回 (session_id, 题目列表)。"""
    store = get_store()
    questions = store.get_random_questions(
        count=question_count,
        paper_id=source_id if source_type == "paper" else None,
        group_id=source_id if source_type == "group" else None,
        q_type=q_type,
    )
    if not questions:
        return -1, []
    session_id = store.create_session(
        source_type=source_type,
        source_id=source_id,
        total=len(questions),
    )
    return session_id, questions


def submit_answer(
    session_id: int,
    question_id: int,
    user_answer: str,
) -> tuple[bool, str]:
    """提交单题答案。返回 (is_correct, explanation)。"""
    store = get_store()
    q = store.get_question(question_id)
    if q is None:
        return False, ""
    is_correct = q.check_answer(user_answer)
    store.add_record(session_id, question_id, user_answer, is_correct)
    return is_correct, q.explanation


def complete_session(session_id: int) -> PracticeSession:
    """结束会话，统计正确数，返回结果。"""
    store = get_store()
    details = store.get_session_detail(session_id)
    correct = sum(1 for d in details if d["is_correct"])
    store.complete_session(session_id, correct)
    sessions = store.list_sessions(limit=1)
    # 重新查询最新状态
    import sqlite3
    from contextlib import closing
    with closing(sqlite3.connect(QUESTION_DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM practice_sessions WHERE id=?", (session_id,)
        ).fetchone()
    if row:
        return PracticeSession(
            id=row["id"],
            source_type=row["source_type"],
            source_id=row["source_id"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            total=row["total"],
            correct=row["correct"],
            status=row["status"],
        )
    return PracticeSession(
        id=session_id,
        source_type="all",
        source_id=None,
        start_time="",
        end_time=None,
        total=len(details),
        correct=correct,
        status="completed",
    )


def get_session_history(limit: int = 50) -> list[PracticeSession]:
    return get_store().list_sessions(limit=limit)
