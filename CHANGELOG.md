# CHANGELOG

## v0.1.0（待发布）
- 题库检索模块：支持 PDF/TXT/CSV/JSON 格式导入
- 语义检索：multilingual-e5-small Embedding，支持中英混合内容
- 向量库：ChromaDB 嵌入式模式，数据持久化
- Streamlit Web UI：题库上传 + 相似题检索
- 内存保护机制（无 Swap 环境安全守卫）
- 单元测试：text_splitter / parsers / vector_store / memory_guard

## v0.2.0（计划中）
- 资料问答模块：PDF/DOCX 文档上传 + RAG 问答
- Ollama qwen2.5:1.5b 本地推理支持
- DeepSeek / 智谱 GLM API 备选后端
- 流式输出 + 来源引用
- 集成测试 + 压力测试
