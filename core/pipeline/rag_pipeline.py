from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Iterator

from config.prompts import RAG_SYSTEM_PROMPT, RAG_USER_TEMPLATE, RAG_CITATION_TEMPLATE
from config.settings import DOCUMENTS_COLLECTION, RETRIEVAL_TOP_K, RETRIEVAL_SCORE_THRESHOLD
from core.parsers import get_parser
from core.providers import get_embedder, get_llm_provider
from core.utils.text_splitter import split_text
from core.vector_store import get_store
from core.vector_store.base_store import Document, SearchResult


def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def import_document(file_path: Path, source_name: str = "") -> int:
    """
    解析文档，分块入库，返回入库的 chunk 数量。
    """
    parser = get_parser(file_path)
    raw_text = parser.parse(file_path)
    if not raw_text.strip():
        return 0

    chunks = split_text(raw_text)
    if not chunks:
        return 0

    embedder = get_embedder()
    store = get_store(DOCUMENTS_COLLECTION)

    name = source_name or file_path.name
    documents = []
    vectors = []

    # 批量向量化
    all_vectors = embedder.embed_documents(chunks)

    for i, (chunk, vec) in enumerate(zip(chunks, all_vectors)):
        doc_id = _md5(f"{name}::{i}::{chunk[:50]}")
        meta = {
            "source_file": name,
            "chunk_index": str(i),
            "chunk_total": str(len(chunks)),
        }
        documents.append(Document(id=doc_id, text=chunk, metadata=meta))
        vectors.append(vec)

    store.add(documents, vectors)
    return len(documents)


def retrieve(query: str, top_k: int = RETRIEVAL_TOP_K) -> list[SearchResult]:
    """从文档库检索相关段落。"""
    embedder = get_embedder()
    store = get_store(DOCUMENTS_COLLECTION)
    query_vector = embedder.embed_query(query)
    return store.search(query_vector, top_k=top_k, score_threshold=RETRIEVAL_SCORE_THRESHOLD)


def answer_stream(question: str, top_k: int = RETRIEVAL_TOP_K) -> Iterator[str]:
    """
    完整 RAG 流程：检索相关段落 → 构建 prompt → 流式生成回答。
    yield 文本片段，最后 yield 来源引用。
    """
    results = retrieve(question, top_k=top_k)

    if not results:
        yield "参考资料中未找到与该问题相关的内容，无法回答。"
        return

    context_parts = []
    sources = []
    for r in results:
        context_parts.append(r.document.text)
        src = r.document.metadata.get("source_file", "未知来源")
        chunk_idx = r.document.metadata.get("chunk_index", "")
        label = f"{src} 第{int(chunk_idx)+1}段" if chunk_idx else src
        if label not in sources:
            sources.append(label)

    context = "\n\n---\n\n".join(context_parts)
    full_prompt = (
        RAG_SYSTEM_PROMPT
        + "\n\n"
        + RAG_USER_TEMPLATE.format(context=context, question=question)
    )

    llm = get_llm_provider()
    yield from llm.generate_stream(full_prompt)

    if sources:
        yield RAG_CITATION_TEMPLATE.format(sources="、".join(sources))


def get_document_count() -> int:
    return get_store(DOCUMENTS_COLLECTION).count()
