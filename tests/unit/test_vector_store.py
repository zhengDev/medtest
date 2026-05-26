import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
import tempfile
import os
from core.vector_store.chroma_store import ChromaStore
from core.vector_store.base_store import Document


@pytest.fixture
def store(tmp_path):
    return ChromaStore("test_collection", persist_dir=str(tmp_path))


def _fake_vector(seed: int, dim: int = 384) -> list[float]:
    import math
    # seed+1 避免 seed=0 时产生全零向量导致除零
    v = [math.sin((seed + 1) * (i + 1) * 0.1) for i in range(dim)]
    norm = math.sqrt(sum(x ** 2 for x in v))
    return [x / norm for x in v]


def test_add_and_count(store):
    docs = [Document(id="1", text="心脏", metadata={})]
    store.add(docs, [_fake_vector(1)])
    assert store.count() == 1


def test_upsert_is_idempotent(store):
    docs = [Document(id="1", text="心脏", metadata={})]
    store.add(docs, [_fake_vector(1)])
    store.add(docs, [_fake_vector(1)])
    assert store.count() == 1


def test_search_returns_results(store):
    docs = [
        Document(id="1", text="心脏解剖", metadata={"subject": "解剖学"}),
        Document(id="2", text="肺部结构", metadata={"subject": "解剖学"}),
    ]
    vecs = [_fake_vector(1), _fake_vector(999)]
    store.add(docs, vecs)
    results = store.search(_fake_vector(1), top_k=2, score_threshold=0.0)
    assert len(results) >= 1
    assert results[0].document.id == "1"


def test_delete(store):
    docs = [Document(id="del1", text="待删除", metadata={})]
    store.add(docs, [_fake_vector(42)])
    assert store.count() == 1
    store.delete("del1")
    assert store.count() == 0


def test_clear(store):
    docs = [Document(id=str(i), text=f"doc{i}", metadata={}) for i in range(5)]
    vecs = [_fake_vector(i) for i in range(5)]
    store.add(docs, vecs)
    assert store.count() == 5
    store.clear()
    assert store.count() == 0
