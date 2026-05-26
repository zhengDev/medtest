import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tempfile
import streamlit as st
from core.pipeline.rag_pipeline import import_document, answer_stream, get_document_count
from core.utils.memory_guard import assert_memory_safe, get_memory_available_mb
from config.settings import SUPPORTED_DOC_EXTENSIONS, MAX_UPLOAD_MB, LLM_PROVIDER

st.set_page_config(page_title="资料问答", page_icon="💬", layout="wide")
st.title("💬 资料问答")

if LLM_PROVIDER == "ollama":
    st.info("当前使用本地 Ollama 推理，CPU 模式下每次回答约需 40-100 秒，请耐心等待。", icon="ℹ️")

# ── 上传区 ──────────────────────────────────────────────────
st.subheader("1. 上传学习资料")
uploaded = st.file_uploader(
    f"支持格式：{', '.join(SUPPORTED_DOC_EXTENSIONS)}，最大 {MAX_UPLOAD_MB}MB",
    type=[e.lstrip(".") for e in SUPPORTED_DOC_EXTENSIONS],
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
                with st.spinner(f"正在解析分块入库 {file.name} ..."):
                    count = import_document(tmp_path, source_name=file.name)
                tmp_path.unlink(missing_ok=True)
                st.success(f"成功导入 {count} 个文本段落")
            except MemoryError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"导入失败：{e}")

st.caption(f"当前资料库共 {get_document_count()} 个段落 | 可用内存 {get_memory_available_mb():.0f}MB")
st.divider()

# ── 问答区 ──────────────────────────────────────────────────
st.subheader("2. 基于资料提问")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if question := st.chat_input("输入您的问题..."):
    if get_document_count() == 0:
        st.warning("资料库为空，请先上传学习资料")
    else:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            try:
                assert_memory_safe()
                response = st.write_stream(answer_stream(question))
                st.session_state.messages.append({"role": "assistant", "content": response})
            except MemoryError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"回答失败：{e}")

if st.session_state.messages and st.button("清空对话记录"):
    st.session_state.messages = []
    st.rerun()
