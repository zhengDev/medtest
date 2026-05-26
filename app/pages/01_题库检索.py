import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tempfile
import streamlit as st
from core.pipeline.question_pipeline import import_questions, search_questions, get_question_count
from core.utils.memory_guard import assert_memory_safe, get_memory_available_mb
from config.settings import SUPPORTED_QUESTION_EXTENSIONS, MAX_UPLOAD_MB

st.set_page_config(page_title="题库检索", page_icon="📚", layout="wide")
st.title("📚 题库检索")

# ── 上传区 ──────────────────────────────────────────────────
st.subheader("1. 上传题库")
uploaded = st.file_uploader(
    f"支持格式：{', '.join(SUPPORTED_QUESTION_EXTENSIONS)}，最大 {MAX_UPLOAD_MB}MB",
    type=[e.lstrip(".") for e in SUPPORTED_QUESTION_EXTENSIONS],
    accept_multiple_files=True,
)

if uploaded:
    for file in uploaded:
        if file.size > MAX_UPLOAD_MB * 1024 * 1024:
            st.error(f"文件 {file.name} 超过 {MAX_UPLOAD_MB}MB 限制")
            continue
        if st.button(f"导入 {file.name}", key=f"import_{file.name}"):
            try:
                assert_memory_safe()
                with tempfile.NamedTemporaryFile(
                    suffix=Path(file.name).suffix, delete=False
                ) as tmp:
                    tmp.write(file.read())
                    tmp_path = Path(tmp.name)
                with st.spinner(f"正在解析并入库 {file.name} ..."):
                    count = import_questions(tmp_path, source_name=file.name)
                tmp_path.unlink(missing_ok=True)
                st.success(f"成功导入 {count} 道题目")
            except MemoryError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"导入失败：{e}")

st.caption(f"当前题库共 {get_question_count()} 道题 | 可用内存 {get_memory_available_mb():.0f}MB")
st.divider()

# ── 检索区 ──────────────────────────────────────────────────
st.subheader("2. 语义检索")
query = st.text_area("输入关键词或完整题目描述", height=100, placeholder="例如：关于心脏结构的描述，正确的是")
top_k = st.slider("返回结果数量", min_value=1, max_value=10, value=5)

if st.button("🔍 检索相似题", type="primary", disabled=not query.strip()):
    if get_question_count() == 0:
        st.warning("题库为空，请先上传题库文件")
    else:
        try:
            assert_memory_safe()
            with st.spinner("检索中..."):
                results = search_questions(query.strip(), top_k=top_k)
            if not results:
                st.info("未找到相似题目，请尝试调整描述或降低相似度要求")
            else:
                st.success(f"找到 {len(results)} 道相似题目")
                for i, r in enumerate(results, 1):
                    with st.expander(
                        f"第 {i} 题 — 相似度 {r.score:.1%}",
                        expanded=(i == 1),
                    ):
                        st.markdown(r.document.text)
                        meta = r.document.metadata
                        cols = st.columns(3)
                        if meta.get("answer"):
                            cols[0].markdown(f"**答案**：{meta['answer']}")
                        if meta.get("subject"):
                            cols[1].markdown(f"**科目**：{meta['subject']}")
                        if meta.get("source_file"):
                            cols[2].caption(f"来源：{meta['source_file']}")
        except MemoryError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"检索失败：{e}")
