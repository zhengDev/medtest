# CHANGELOG

## v0.1.0（2026-05-26）
- 题库检索模块：支持 PDF/TXT/CSV/JSON 格式导入
- 语义检索：multilingual-e5-small Embedding，支持中英混合内容
- 向量库：ChromaDB 嵌入式模式，数据持久化
- Streamlit Web UI：题库上传 + 相似题检索
- 内存保护机制（无 Swap 环境安全守卫）
- 集成测试：题库导入全流程（TXT/CSV/JSON）、语义检索召回验证
- 单元测试：text_splitter / parsers / vector_store / memory_guard（31/31 通过）
- 关键修复：Embedding 模型 ID（intfloat）、ChromaStore 测试隔离、E5Embedder pytest 兼容

## v0.2.0（计划中）
- 资料问答模块：PDF/DOCX 文档上传 + RAG 问答
- Ollama qwen2.5:1.5b 本地推理支持
- DeepSeek / 智谱 GLM API 备选后端
- 流式输出 + 来源引用
- 集成测试 + 压力测试
