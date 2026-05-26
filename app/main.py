import sys
from pathlib import Path

# 确保项目根目录在 sys.path，支持从任意目录启动
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import psutil
from core.providers import get_llm_provider
from config.settings import LLM_PROVIDER

st.set_page_config(
    page_title="医学知识库",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _memory_bar() -> None:
    mem = psutil.virtual_memory()
    used_mb = mem.used / 1024 / 1024
    total_mb = mem.total / 1024 / 1024
    pct = mem.percent
    color = "🟢" if pct < 70 else ("🟡" if pct < 85 else "🔴")
    st.sidebar.metric(
        label=f"{color} 内存使用",
        value=f"{used_mb:.0f} MB",
        delta=f"{total_mb:.0f} MB 总计",
    )
    st.sidebar.progress(int(pct))


def _llm_status() -> None:
    if LLM_PROVIDER == "ollama":
        try:
            ok = get_llm_provider().health_check()
            st.sidebar.markdown(f"**LLM 服务**：{'🟢 Ollama 在线' if ok else '🔴 Ollama 离线'}")
        except Exception:
            st.sidebar.markdown("**LLM 服务**：🔴 连接失败")
    else:
        st.sidebar.markdown(f"**LLM 服务**：🌐 {LLM_PROVIDER.upper()} API")


with st.sidebar:
    st.title("🏥 医学知识库")
    st.divider()
    _memory_bar()
    _llm_status()
    st.divider()
    st.caption("使用左侧导航栏切换功能模块")

st.title("欢迎使用医学知识库系统")
st.markdown("""
### 功能模块
- **📚 题库检索**：上传试卷 PDF/TXT/CSV，语义搜索相似题目
- **💬 资料问答**：上传学习资料，基于文档内容进行问答推理

请从左侧导航栏选择功能模块开始使用。
""")
