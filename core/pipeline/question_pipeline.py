from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path

from config.settings import QUESTIONS_COLLECTION, RETRIEVAL_TOP_K, RETRIEVAL_SCORE_THRESHOLD
from core.parsers import get_parser
from core.providers import get_embedder
from core.utils.text_splitter import split_text
from core.vector_store import get_store
from core.vector_store.base_store import Document, SearchResult


def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _parse_questions_from_text(text: str) -> list[dict]:
    """将纯文本按空行分割成题目列表，每道题作为独立 document。"""
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    return [{"text": b, "metadata": {}} for b in blocks]


def _parse_questions_from_csv(file_path: Path) -> list[dict]:
    questions = []
    with open(file_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = row.get("question", "") + "\n" + row.get("options", "")
            meta = {k: v for k, v in row.items() if k not in ("question", "options")}
            if text.strip():
                questions.append({"text": text.strip(), "metadata": meta})
    return questions


def _parse_questions_from_json(file_path: Path) -> list[dict]:
    data = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        data = [data]
    questions = []
    for item in data:
        text = item.get("question", "") + "\n" + str(item.get("options", ""))
        meta = {k: str(v) for k, v in item.items() if k != "question" and k != "options"}
        if text.strip():
            questions.append({"text": text.strip(), "metadata": meta})
    return questions


def import_questions(file_path: Path, source_name: str = "") -> int:
    """
    解析题库文件并入库，返回新增题目数量。
    使用题干 MD5 作为 ID，支持幂等导入（重复上传同一文件不会重复插入）。
    """
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        questions = _parse_questions_from_csv(file_path)
    elif suffix == ".json":
        questions = _parse_questions_from_json(file_path)
    else:
        # PDF 和 TXT 通过解析器获取文本后按段落分割
        parser = get_parser(file_path)
        raw_text = parser.parse(file_path)
        questions = _parse_questions_from_text(raw_text)

    if not questions:
        return 0

    embedder = get_embedder()
    store = get_store(QUESTIONS_COLLECTION)

    texts = [q["text"] for q in questions]
    vectors = embedder.embed_documents(texts)

    documents = []
    for q, vec in zip(questions, vectors):
        doc_id = _md5(q["text"])
        meta = {**q["metadata"], "source_file": source_name or file_path.name}
        documents.append(Document(id=doc_id, text=q["text"], metadata=meta))

    store.add(documents, vectors)
    return len(documents)


def search_questions(query: str, top_k: int = RETRIEVAL_TOP_K) -> list[SearchResult]:
    """语义检索相似题目，不调用 LLM，响应 < 1 秒。"""
    embedder = get_embedder()
    store = get_store(QUESTIONS_COLLECTION)
    query_vector = embedder.embed_query(query)
    return store.search(query_vector, top_k=top_k, score_threshold=RETRIEVAL_SCORE_THRESHOLD)


def get_question_count() -> int:
    return get_store(QUESTIONS_COLLECTION).count()
