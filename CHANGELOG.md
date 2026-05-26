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

## v0.2.0（2026-05-26）
- 资料问答模块：PDF/DOCX/TXT 文档上传 + RAG 流式问答
- Ollama qwen2.5:1.5b 本地推理（CPU 实测 12.5 字符/秒，内存增量 1186MB）
- DeepSeek / 智谱 GLM API 备选后端（切换只需改 settings.py 一行）
- 流式输出（Streamlit write_stream）+ 来源段落引用
- LLM Provider 单元测试（mock HTTP）+ RAG 端到端集成测试（40/40 通过）
- Ollama 性能摸底报告：双模块同时运行内存峰值 2243MB/3594MB，可用余量 1.35GB

## v0.3.0（计划中）
- systemd 自启服务配置
- 日志轮转（logrotate）
- 定期健康检查脚本
- 数据备份脚本（chroma_db 定时打包）
