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

## v0.4.0（2026-05-27）
- 题库模块全面重构：语义检索 → 交互式练习系统
- SQLite 结构化存储（不依赖 ChromaDB / Embedding），无额外内存消耗
- SmartQuestionParser：正则解析中文试卷（单选/多选/判断/填空/简答），支持 PDF/TXT/CSV/JSON
- 答案规范化：多选自动排序（BA→AB）、判断转 T/F（√/×/正确/错误）
- 幂等导入：MD5(stem) 去重，同一题目重复导入自动跳过
- 4-Tab Streamlit UI：导入试卷 / 题目练习（状态机）/ 题库管理 / 练习记录
- 练习交互：单选 radio、多选 multiselect、判断双按钮、填空文本框、简答查看答案
- 练习结束汇总：正确率统计 + 错题复盘
- 题库管理：按试卷/按分组切换，题目分页浏览，自定义分组增删
- 练习记录：历史会话列表 + 按题展开错题回顾
- 新增 23 个单元测试，总测试 63/63 全部通过

## v0.3.0（2026-05-26）
- systemd 服务：/etc/systemd/system/medtest.service（开机自启，随 ollama.service 一起）
- 日志轮转：/etc/logrotate.d/medtest（daily，保留 7 天，压缩）
- 定时备份：cron 每天凌晨 3 点执行 scripts/backup.sh，保留最近 7 份
- 健康检查：scripts/health_check.py 全部通过（内存 1460MB 可用，Ollama 在线）
