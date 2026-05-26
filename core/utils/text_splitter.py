from __future__ import annotations
from config.settings import CHUNK_SIZE, CHUNK_OVERLAP


# 中英文递归分割优先级
_SEPARATORS = ["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]


def split_text(text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> list[str]:
    """递归按分隔符切分，保证每块不超过 chunk_size 字符，相邻块重叠 chunk_overlap 字符。"""
    chunks = _split_recursive(text.strip(), chunk_size, _SEPARATORS)
    return _merge_with_overlap(chunks, chunk_size, chunk_overlap)


def _split_recursive(text: str, chunk_size: int, separators: list[str]) -> list[str]:
    if len(text) <= chunk_size:
        return [text] if text else []

    for sep in separators:
        if sep and sep in text:
            parts = text.split(sep)
            results = []
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                if len(part) <= chunk_size:
                    results.append(part)
                else:
                    results.extend(_split_recursive(part, chunk_size, separators[separators.index(sep) + 1:]))
            return results

    # 无任何分隔符可用，按字数强制截断
    return [text[i: i + chunk_size] for i in range(0, len(text), chunk_size)]


def _merge_with_overlap(chunks: list[str], chunk_size: int, overlap: int) -> list[str]:
    """将过小的碎片合并，并在相邻块之间保留重叠。"""
    if not chunks:
        return []

    merged: list[str] = []
    current = chunks[0]

    for next_chunk in chunks[1:]:
        if len(current) + len(next_chunk) + 1 <= chunk_size:
            current = current + "\n" + next_chunk
        else:
            merged.append(current)
            # 重叠：取 current 末尾 overlap 字符作为下一块开头
            overlap_text = current[-overlap:] if overlap > 0 else ""
            current = (overlap_text + "\n" + next_chunk).strip() if overlap_text else next_chunk

    merged.append(current)
    return [c for c in merged if c.strip()]
