"""
SmartQuestionParser：从 PDF/TXT 提取的纯文本中识别中文试卷格式。

支持的格式：
  - 有编号题目：1. / 1、/ 1） / （1）
  - 无编号题目：空行分隔
  - 选项：A. / A、/ A） / 同行多选项 "A.文字  B.文字"
  - 答案行：答案：B / 【答案】B / 参考答案：AB
  - 解析行：解析：... / 【解析】...
  - 大题标题：一、单选题 / 二、多选题 等（用于推断题型）
"""
from __future__ import annotations
import hashlib
import json
import logging
import re
from typing import Optional

from core.question_bank.models import (
    Question,
    Q_TYPE_SINGLE, Q_TYPE_MULTI, Q_TYPE_JUDGE, Q_TYPE_FILL, Q_TYPE_ESSAY,
)

logger = logging.getLogger(__name__)

# ── 正则模式 ──────────────────────────────────────────────────

# 题号：1. / 1、/ 1） / （1）
RE_Q_NUM = re.compile(
    r'(?:^|\n)[ \t]*(?:[（(]\s*\d+\s*[）)]|\d+\s*[\.。、\)）])\s*',
)

# 选项行：A. / A、/ A） / （A）  （仅行首）
RE_OPTION_LINE = re.compile(
    r'^([A-Fa-f])\s*[\.。、\)）]\s*(.+)$',
    re.MULTILINE,
)

# 同行多个选项：A.文字  B.文字  C.文字
RE_INLINE_OPTIONS = re.compile(
    r'(?:^|(?<=\s))([A-Fa-f])[\.、\)）]\s*([^A-Fa-f\n]{1,60}?)(?=\s+[A-Fa-f][\.、\)）]|$)',
    re.MULTILINE,
)

# 答案行
RE_ANSWER = re.compile(
    r'^(?:参考\s*)?答案\s*[：:]\s*(.+)$',
    re.MULTILINE,
)

# 解析行（可跨行，到下一题号或文本末尾）
RE_EXPLAIN = re.compile(
    r'^解析\s*[：:]\s*(.+?)(?=(?:^|\n)\s*\d+\s*[\.。、\)）]|\Z)',
    re.MULTILINE | re.DOTALL,
)

# 填空符号
RE_FILL_MARK = re.compile(r'_{2,}|（\s{2,}）|\(\s{2,}\)|____')

# 大题标题（用于推断 section_type）
RE_SECTION = re.compile(
    r'^[一二三四五六七八九十]+\s*[、.．]\s*(.{1,20}题)',
    re.MULTILINE,
)

# 全角数字/字母→半角映射
_FULLWIDTH = str.maketrans(
    "　！＂＃＄％＆＇（）＊＋，－．／０１２３４５６７８９：；＜＝＞？＠"
    "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ［＼］＾＿｀"
    "ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ｛｜｝～",
    " !\"#$%&'()*+,-./" + "0123456789:;<=>?@"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`"
    "abcdefghijklmnopqrstuvwxyz{|}~",
)

# 大题标题关键词 → 题型
_SECTION_TYPE_MAP = {
    "单选": Q_TYPE_SINGLE, "最佳选择": Q_TYPE_SINGLE,
    "多选": Q_TYPE_MULTI,  "多项": Q_TYPE_MULTI,
    "判断": Q_TYPE_JUDGE,  "是非": Q_TYPE_JUDGE,
    "填空": Q_TYPE_FILL,
    "简答": Q_TYPE_ESSAY,  "问答": Q_TYPE_ESSAY, "论述": Q_TYPE_ESSAY,
}

# 答案标准化
_JUDGE_NORM = {
    "T": "T", "F": "F",
    "√": "T", "×": "F",
    "对": "T", "错": "F",
    "正确": "T", "错误": "F",
    "是": "T", "否": "F",
    "Y": "T", "N": "F",
}


def _md5(text: str) -> str:
    return hashlib.md5(text.strip().encode("utf-8")).hexdigest()


def _normalize_answer(answer: str, q_type: str) -> str:
    a = answer.strip().upper()
    if q_type == Q_TYPE_JUDGE:
        return _JUDGE_NORM.get(a, _JUDGE_NORM.get(answer.strip(), "T"))
    if q_type in (Q_TYPE_SINGLE, Q_TYPE_MULTI):
        # 只保留字母，排序
        letters = "".join(sorted(set(c for c in a if c.isalpha())))
        return letters if letters else a
    return answer.strip()


class SmartQuestionParser:
    """从纯文本中识别中文试卷结构，返回 Question 列表。"""

    def parse_text(
        self,
        text: str,
        paper_id: Optional[int] = None,
    ) -> list[Question]:
        """主入口：全文解析，返回 Question 列表（不含 id，未入库）。"""
        text = self._preprocess(text)
        if not text.strip():
            return []

        questions: list[Question] = []

        # 尝试按大题标题分段
        sections = self._split_sections(text)

        for section_text, section_type in sections:
            blocks = self._extract_blocks(section_text)
            for block in blocks:
                q = self._parse_block(block.strip(), section_type, paper_id)
                if q and len(q.stem.strip()) >= 4:
                    questions.append(q)

        return questions

    def parse_csv_row(self, row: dict, paper_id: Optional[int] = None) -> Optional[Question]:
        """解析单行 CSV（兼容旧格式）。"""
        stem = (row.get("question") or "").strip()
        if not stem:
            return None
        options_raw = row.get("options", "")
        options = self._parse_options_string(str(options_raw)) if options_raw else {}
        answer = str(row.get("answer", "")).strip()

        q_type = Q_TYPE_SINGLE if options else Q_TYPE_ESSAY
        if options and len(answer) > 1:
            q_type = Q_TYPE_MULTI

        meta = {k: v for k, v in row.items() if k not in ("question", "options", "answer", "explanation")}
        return Question(
            id=None,
            paper_id=paper_id,
            q_hash=_md5(stem),
            q_type=q_type,
            stem=stem,
            options=options,
            answer=_normalize_answer(answer, q_type),
            explanation=str(row.get("explanation", "")),
            subject=str(row.get("subject", "")),
        )

    def parse_json_item(self, item: dict, paper_id: Optional[int] = None) -> Optional[Question]:
        """解析单个 JSON 对象（兼容旧格式）。"""
        stem = (item.get("question") or "").strip()
        if not stem:
            return None
        options_raw = item.get("options", {})
        if isinstance(options_raw, dict):
            options = {k.upper(): str(v) for k, v in options_raw.items()}
        elif isinstance(options_raw, str):
            options = self._parse_options_string(options_raw)
        else:
            options = {}

        answer = str(item.get("answer", "")).strip()
        q_type = Q_TYPE_SINGLE if options else Q_TYPE_ESSAY
        if options and len(answer) > 1 and all(c.upper() in options for c in answer):
            q_type = Q_TYPE_MULTI

        return Question(
            id=None,
            paper_id=paper_id,
            q_hash=_md5(stem),
            q_type=q_type,
            stem=stem,
            options=options,
            answer=_normalize_answer(answer, q_type),
            explanation=str(item.get("explanation", "")),
            subject=str(item.get("subject", "")),
        )

    # ── 内部方法 ──────────────────────────────────────────────

    def _preprocess(self, text: str) -> str:
        text = text.translate(_FULLWIDTH)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # 去除常见页眉页脚（单独一行且极短的纯数字行）
        lines = [ln for ln in text.split("\n") if not re.match(r'^\s*-?\s*\d{1,3}\s*-?\s*$', ln)]
        return "\n".join(lines)

    def _split_sections(self, text: str) -> list[tuple[str, str]]:
        """按大题标题切分，返回 [(section_text, section_type)]。"""
        sections: list[tuple[str, str]] = []
        matches = list(RE_SECTION.finditer(text))
        if not matches:
            return [(text, "")]

        # 第一个标题之前的文本
        if matches[0].start() > 0:
            sections.append((text[: matches[0].start()], ""))

        for i, m in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section_text = text[m.end(): end]
            title = m.group(1)
            stype = ""
            for kw, qt in _SECTION_TYPE_MAP.items():
                if kw in title:
                    stype = qt
                    break
            sections.append((section_text, stype))

        return sections

    def _extract_blocks(self, text: str) -> list[str]:
        """在段落内按题号切出题目块；若无题号则按空行切分。"""
        positions = [(m.start(), m.end()) for m in RE_Q_NUM.finditer(text)]

        if len(positions) >= 2:
            blocks = []
            for i, (start, content_start) in enumerate(positions):
                end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
                blocks.append(text[content_start:end])
            return [b.strip() for b in blocks if b.strip()]
        else:
            # 无编号：空行分隔
            blocks = [b.strip() for b in re.split(r'\n\s*\n', text) if b.strip()]
            return blocks

    def _parse_block(
        self,
        block: str,
        section_type: str,
        paper_id: Optional[int],
    ) -> Optional[Question]:
        """解析单个题目块，失败返回 None。"""
        try:
            # 提取答案
            answer_match = RE_ANSWER.search(block)
            answer_raw = answer_match.group(1).strip() if answer_match else ""

            # 提取解析
            explain_match = RE_EXPLAIN.search(block)
            explanation = explain_match.group(1).strip() if explain_match else ""

            # 提取选项（优先多行，退回同行）
            options = self._extract_options_multiline(block)
            if not options:
                options = self._extract_options_inline(block)

            # 去掉选项行、答案行、解析行，剩余为题干
            stem = block
            for pattern in [RE_OPTION_LINE, RE_ANSWER, RE_EXPLAIN]:
                stem = pattern.sub("", stem)
            # 去掉同行选项残留（如果有）
            if not options:
                pass
            else:
                # 去掉每个选项文字
                for letter, text in options.items():
                    stem = re.sub(
                        rf'[{letter.upper()}{letter.lower()}]\s*[\.、\)）]\s*{re.escape(text)}',
                        "", stem
                    )
            stem = stem.strip()
            # 去掉题号残留（行首数字+标点）
            stem = re.sub(r'^\s*\d+\s*[\.、\)）]\s*', '', stem, flags=re.MULTILINE)
            stem = stem.strip()

            if not stem:
                return None

            # 推断题型
            q_type = self._infer_type(options, answer_raw, stem, section_type)

            # 规范化答案
            answer = _normalize_answer(answer_raw, q_type) if answer_raw else ""

            return Question(
                id=None,
                paper_id=paper_id,
                q_hash=_md5(stem),
                q_type=q_type,
                stem=stem,
                options=options,
                answer=answer,
                explanation=explanation,
            )
        except Exception as e:
            logger.debug("parse_block failed: %s | block: %s", e, block[:60])
            return None

    def _extract_options_multiline(self, block: str) -> dict[str, str]:
        """提取多行选项（每个选项占一行）。"""
        options = {}
        for m in RE_OPTION_LINE.finditer(block):
            letter = m.group(1).upper()
            text = m.group(2).strip()
            options[letter] = text
        return options

    def _extract_options_inline(self, block: str) -> dict[str, str]:
        """提取同行多选项（A.文字 B.文字 C.文字）。"""
        options = {}
        for m in RE_INLINE_OPTIONS.finditer(block):
            letter = m.group(1).upper()
            text = m.group(2).strip()
            if text:
                options[letter] = text
        return options if len(options) >= 2 else {}

    def _parse_options_string(self, raw: str) -> dict[str, str]:
        """解析 CSV 中的选项字符串，如 'A.最薄 B.最厚 C.与右心室等厚'。"""
        options = self._extract_options_multiline(raw)
        if not options:
            options = self._extract_options_inline(raw)
        return options

    @staticmethod
    def _infer_type(
        options: dict,
        answer: str,
        stem: str,
        section_type: str,
    ) -> str:
        # 大题标题给出的类型优先
        if section_type in (Q_TYPE_SINGLE, Q_TYPE_MULTI, Q_TYPE_JUDGE, Q_TYPE_FILL, Q_TYPE_ESSAY):
            return section_type

        if options:
            # 判断题：只有"正确"/"错误"两个选项
            opt_texts = {v.strip() for v in options.values()}
            if opt_texts <= {"正确", "错误", "A", "B", "√", "×"}:
                if len(options) == 2:
                    return Q_TYPE_JUDGE
            # 答案含多个字母 → 多选
            if len(answer) > 1 and all(c.upper() in options for c in answer if c.isalpha()):
                return Q_TYPE_MULTI
            return Q_TYPE_SINGLE

        # 无选项：看答案
        norm_ans = answer.strip().upper()
        if norm_ans in {"T", "F", "√", "×", "正确", "错误", "对", "错"}:
            return Q_TYPE_JUDGE

        # 看题干有无填空符
        if RE_FILL_MARK.search(stem):
            return Q_TYPE_FILL

        return Q_TYPE_ESSAY
