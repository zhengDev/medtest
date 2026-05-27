from __future__ import annotations
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from typing import Optional

from core.question_bank.models import (
    Question, PracticeSession, PracticeRecord,
)

_SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS exam_papers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    source_file TEXT    NOT NULL,
    import_time TEXT    NOT NULL,
    total_count INTEGER NOT NULL DEFAULT 0,
    description TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS questions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id     INTEGER REFERENCES exam_papers(id) ON DELETE CASCADE,
    q_hash       TEXT    NOT NULL UNIQUE,
    q_type       TEXT    NOT NULL,
    stem         TEXT    NOT NULL,
    options_json TEXT    NOT NULL DEFAULT '{}',
    answer       TEXT    NOT NULL DEFAULT '',
    explanation  TEXT    DEFAULT '',
    subject      TEXT    DEFAULT '',
    difficulty   INTEGER DEFAULT 2,
    import_time  TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_q_paper ON questions(paper_id);
CREATE INDEX IF NOT EXISTS idx_q_type  ON questions(q_type);

CREATE TABLE IF NOT EXISTS question_groups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    description TEXT    DEFAULT '',
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS question_group_map (
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    group_id    INTEGER NOT NULL REFERENCES question_groups(id) ON DELETE CASCADE,
    PRIMARY KEY (question_id, group_id)
);

CREATE TABLE IF NOT EXISTS practice_sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT    NOT NULL,
    source_id   INTEGER DEFAULT NULL,
    start_time  TEXT    NOT NULL,
    end_time    TEXT    DEFAULT NULL,
    total       INTEGER NOT NULL DEFAULT 0,
    correct     INTEGER NOT NULL DEFAULT 0,
    status      TEXT    NOT NULL DEFAULT 'in_progress'
);

CREATE TABLE IF NOT EXISTS practice_records (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER NOT NULL REFERENCES practice_sessions(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    user_answer TEXT    NOT NULL,
    is_correct  INTEGER NOT NULL,
    answered_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rec_session ON practice_records(session_id);
"""


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _row_to_question(row) -> Question:
    return Question(
        id=row["id"],
        paper_id=row["paper_id"],
        q_hash=row["q_hash"],
        q_type=row["q_type"],
        stem=row["stem"],
        options=json.loads(row["options_json"] or "{}"),
        answer=row["answer"],
        explanation=row["explanation"] or "",
        subject=row["subject"] or "",
        difficulty=row["difficulty"] or 2,
        import_time=row["import_time"],
    )


class QuestionStore:
    """SQLite 持久化层，每次操作新建连接（WAL 模式支持读写并发）。"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _conn(self) -> closing:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        return closing(conn)

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(_SCHEMA_SQL)
            conn.commit()

    # ── 试卷管理 ─────────────────────────────────────────────

    def create_paper(self, name: str, source_file: str, description: str = "") -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO exam_papers (name, source_file, import_time, description) VALUES (?,?,?,?)",
                (name, source_file, _now_iso(), description),
            )
            conn.commit()
            return cur.lastrowid

    def update_paper_count(self, paper_id: int, count: int) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE exam_papers SET total_count=? WHERE id=?", (count, paper_id)
            )
            conn.commit()

    def list_papers(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, name, source_file, import_time, total_count, description "
                "FROM exam_papers ORDER BY import_time DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_paper(self, paper_id: int) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM exam_papers WHERE id=?", (paper_id,)
            ).fetchone()
            return dict(row) if row else None

    def delete_paper(self, paper_id: int) -> int:
        with self._conn() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM questions WHERE paper_id=?", (paper_id,)
            ).fetchone()[0]
            conn.execute("DELETE FROM exam_papers WHERE id=?", (paper_id,))
            conn.commit()
            return count

    # ── 题目 CRUD ────────────────────────────────────────────

    def add_questions(self, questions: list[Question], paper_id: int) -> tuple[int, int]:
        """批量插入，跳过已存在的 q_hash。返回 (inserted, skipped)。"""
        inserted = 0
        skipped = 0
        now = _now_iso()
        with self._conn() as conn:
            for q in questions:
                try:
                    conn.execute(
                        """INSERT OR IGNORE INTO questions
                           (paper_id, q_hash, q_type, stem, options_json,
                            answer, explanation, subject, difficulty, import_time)
                           VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (
                            paper_id, q.q_hash, q.q_type, q.stem,
                            json.dumps(q.options, ensure_ascii=False),
                            q.answer, q.explanation, q.subject,
                            q.difficulty, now,
                        ),
                    )
                    if conn.execute(
                        "SELECT changes()"
                    ).fetchone()[0] > 0:
                        inserted += 1
                    else:
                        skipped += 1
                except Exception:
                    skipped += 1
            conn.commit()
        return inserted, skipped

    def get_question(self, question_id: int) -> Optional[Question]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM questions WHERE id=?", (question_id,)
            ).fetchone()
            return _row_to_question(row) if row else None

    def list_questions(
        self,
        paper_id: Optional[int] = None,
        group_id: Optional[int] = None,
        q_type: Optional[str] = None,
        subject: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Question]:
        conditions = []
        params: list = []
        if group_id is not None:
            conditions.append(
                "q.id IN (SELECT question_id FROM question_group_map WHERE group_id=?)"
            )
            params.append(group_id)
        elif paper_id is not None:
            conditions.append("q.paper_id=?")
            params.append(paper_id)
        if q_type:
            conditions.append("q.q_type=?")
            params.append(q_type)
        if subject:
            conditions.append("q.subject=?")
            params.append(subject)
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        params += [limit, offset]
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT q.* FROM questions q {where} ORDER BY q.id LIMIT ? OFFSET ?",
                params,
            ).fetchall()
            return [_row_to_question(r) for r in rows]

    def count_questions(
        self,
        paper_id: Optional[int] = None,
        group_id: Optional[int] = None,
    ) -> int:
        if group_id is not None:
            sql = "SELECT COUNT(*) FROM question_group_map WHERE group_id=?"
            params = [group_id]
        elif paper_id is not None:
            sql = "SELECT COUNT(*) FROM questions WHERE paper_id=?"
            params = [paper_id]
        else:
            sql = "SELECT COUNT(*) FROM questions"
            params = []
        with self._conn() as conn:
            return conn.execute(sql, params).fetchone()[0]

    def get_random_questions(
        self,
        count: int,
        paper_id: Optional[int] = None,
        group_id: Optional[int] = None,
        q_type: Optional[str] = None,
    ) -> list[Question]:
        conditions = []
        params: list = []
        if group_id is not None:
            conditions.append(
                "q.id IN (SELECT question_id FROM question_group_map WHERE group_id=?)"
            )
            params.append(group_id)
        elif paper_id is not None:
            conditions.append("q.paper_id=?")
            params.append(paper_id)
        if q_type:
            conditions.append("q.q_type=?")
            params.append(q_type)
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        params.append(count)
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT q.* FROM questions q {where} ORDER BY RANDOM() LIMIT ?",
                params,
            ).fetchall()
            return [_row_to_question(r) for r in rows]

    def update_question(self, q: Question) -> None:
        with self._conn() as conn:
            conn.execute(
                """UPDATE questions SET q_type=?, stem=?, options_json=?,
                   answer=?, explanation=?, subject=?, difficulty=?
                   WHERE id=?""",
                (
                    q.q_type, q.stem,
                    json.dumps(q.options, ensure_ascii=False),
                    q.answer, q.explanation, q.subject, q.difficulty,
                    q.id,
                ),
            )
            conn.commit()

    def delete_question(self, question_id: int) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM questions WHERE id=?", (question_id,))
            conn.commit()

    # ── 分组管理 ─────────────────────────────────────────────

    def create_group(self, name: str, description: str = "") -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO question_groups (name, description, created_at) VALUES (?,?,?)",
                (name, description, _now_iso()),
            )
            conn.commit()
            return cur.lastrowid

    def list_groups(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT g.id, g.name, g.description, g.created_at,
                          COUNT(m.question_id) AS question_count
                   FROM question_groups g
                   LEFT JOIN question_group_map m ON m.group_id=g.id
                   GROUP BY g.id ORDER BY g.created_at DESC"""
            ).fetchall()
            return [dict(r) for r in rows]

    def add_to_group(self, question_ids: list[int], group_id: int) -> None:
        with self._conn() as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO question_group_map (question_id, group_id) VALUES (?,?)",
                [(qid, group_id) for qid in question_ids],
            )
            conn.commit()

    def remove_from_group(self, question_ids: list[int], group_id: int) -> None:
        with self._conn() as conn:
            conn.executemany(
                "DELETE FROM question_group_map WHERE question_id=? AND group_id=?",
                [(qid, group_id) for qid in question_ids],
            )
            conn.commit()

    def delete_group(self, group_id: int) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM question_groups WHERE id=?", (group_id,))
            conn.commit()

    # ── 练习会话 ─────────────────────────────────────────────

    def create_session(
        self,
        source_type: str,
        source_id: Optional[int],
        total: int,
    ) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO practice_sessions
                   (source_type, source_id, start_time, total)
                   VALUES (?,?,?,?)""",
                (source_type, source_id, _now_iso(), total),
            )
            conn.commit()
            return cur.lastrowid

    def add_record(
        self,
        session_id: int,
        question_id: int,
        user_answer: str,
        is_correct: bool,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO practice_records
                   (session_id, question_id, user_answer, is_correct, answered_at)
                   VALUES (?,?,?,?,?)""",
                (session_id, question_id, user_answer, int(is_correct), _now_iso()),
            )
            conn.commit()

    def complete_session(self, session_id: int, correct: int) -> None:
        with self._conn() as conn:
            conn.execute(
                """UPDATE practice_sessions
                   SET end_time=?, correct=?, status='completed'
                   WHERE id=?""",
                (_now_iso(), correct, session_id),
            )
            conn.commit()

    def list_sessions(self, limit: int = 50) -> list[PracticeSession]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM practice_sessions ORDER BY start_time DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [
                PracticeSession(
                    id=r["id"],
                    source_type=r["source_type"],
                    source_id=r["source_id"],
                    start_time=r["start_time"],
                    end_time=r["end_time"],
                    total=r["total"],
                    correct=r["correct"],
                    status=r["status"],
                )
                for r in rows
            ]

    def get_session_detail(self, session_id: int) -> list[dict]:
        """返回会话的每道题详情（含题干、用户答案、标准答案）。"""
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT r.user_answer, r.is_correct, r.answered_at,
                          q.stem, q.q_type, q.options_json,
                          q.answer AS correct_answer, q.explanation, q.id AS question_id
                   FROM practice_records r
                   JOIN questions q ON r.question_id = q.id
                   WHERE r.session_id=?
                   ORDER BY r.id""",
                (session_id,),
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["options"] = json.loads(d.pop("options_json") or "{}")
                result.append(d)
            return result

    def get_subjects(self) -> list[str]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT subject FROM questions WHERE subject != '' ORDER BY subject"
            ).fetchall()
            return [r[0] for r in rows]
