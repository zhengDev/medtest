from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

Q_TYPE_SINGLE = "single"   # 单选题
Q_TYPE_MULTI  = "multi"    # 多选题
Q_TYPE_JUDGE  = "judge"    # 判断题
Q_TYPE_FILL   = "fill"     # 填空题
Q_TYPE_ESSAY  = "essay"    # 简答/问答题

VALID_Q_TYPES = {Q_TYPE_SINGLE, Q_TYPE_MULTI, Q_TYPE_JUDGE, Q_TYPE_FILL, Q_TYPE_ESSAY}

Q_TYPE_LABELS = {
    Q_TYPE_SINGLE: "单选题",
    Q_TYPE_MULTI:  "多选题",
    Q_TYPE_JUDGE:  "判断题",
    Q_TYPE_FILL:   "填空题",
    Q_TYPE_ESSAY:  "简答题",
}


@dataclass
class Question:
    id:          Optional[int]       # None 表示未入库
    paper_id:    Optional[int]
    q_hash:      str                 # MD5(stem)，幂等键
    q_type:      str                 # VALID_Q_TYPES 之一
    stem:        str                 # 题干
    options:     dict[str, str]      # {"A": "...", "B": "..."}，非选择题为 {}
    answer:      str                 # "B" / "AB" / "T" / 填空答案
    explanation: str = ""
    subject:     str = ""
    difficulty:  int = 2             # 1=易 2=中 3=难
    import_time: str = ""

    @property
    def type_label(self) -> str:
        return Q_TYPE_LABELS.get(self.q_type, self.q_type)

    def check_answer(self, user_answer: str) -> bool:
        """比较用户答案与标准答案（宽松匹配）。"""
        expected = self.answer.strip().upper()
        given = user_answer.strip().upper()
        if self.q_type in (Q_TYPE_SINGLE, Q_TYPE_MULTI):
            # 多选题字母排序后比较
            return "".join(sorted(expected)) == "".join(sorted(given))
        if self.q_type == Q_TYPE_JUDGE:
            # 统一成 T/F
            norm_map = {"T": "T", "F": "F", "√": "T", "×": "F",
                        "对": "T", "错": "F", "正确": "T", "错误": "F",
                        "是": "T", "否": "F", "Y": "T", "N": "F"}
            return norm_map.get(expected, expected) == norm_map.get(given, given)
        if self.q_type == Q_TYPE_FILL:
            return expected == given
        # essay 题不自动判断
        return False


@dataclass
class PracticeSession:
    id:          Optional[int]
    source_type: str                 # 'paper' / 'group' / 'all'
    source_id:   Optional[int]
    start_time:  str
    end_time:    Optional[str]
    total:       int = 0
    correct:     int = 0
    status:      str = "in_progress"

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total > 0 else 0.0


@dataclass
class PracticeRecord:
    id:           Optional[int]
    session_id:   int
    question_id:  int
    user_answer:  str
    is_correct:   bool
    answered_at:  str
