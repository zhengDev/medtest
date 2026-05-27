# MedTest 医学知识库系统

本地部署的医学 RAG 知识库，包含**题目练习**和**资料问答**两个模块。
无需 GPU，适合 2 核 4GB 云服务器。

---

## 快速访问

启动后打开浏览器访问：`http://<服务器IP>:8501`

---

## 服务管理

```bash
# 启动服务
systemctl start medtest

# 停止服务
systemctl stop medtest

# 重启服务（修改代码后执行）
systemctl restart medtest

# 查看运行状态
systemctl status medtest

# 开机自启（已默认开启）
systemctl enable medtest

# 查看实时日志
tail -f /home/zh/medtest/logs/streamlit.log
```

---

## 题目练习模块

### 支持的题目格式

导入文件支持以下格式：

| 格式 | 说明 |
|------|------|
| `.txt` / `.pdf` | 中文试卷纯文本，自动识别题号、选项、答案、解析 |
| `.csv` | 列名：`question,options,answer,subject,explanation` |
| `.json` | 数组格式：`[{"question":"...", "options":{...}, "answer":"..."}]` |

**TXT/PDF 格式示例：**
```
1. 左心室壁比右心室壁厚，这是因为：
A. 左心室负责体循环，压力更大
B. 左心室负责肺循环，压力更大
C. 左右心室壁厚度相同
D. 右心室壁更厚
答案：A
解析：左心室需要泵血至全身，压力约为右心室的5-6倍。
```

**支持的题型：**
- 单选题：答案为单个字母（A/B/C/D）
- 多选题：答案为多个字母（AB/ACD 等，自动排序）
- 判断题：答案为 A（正确）/B（错误），或 √/×/T/F/正确/错误
- 填空题：题干含 `____` 下划线
- 简答题：无选项的开放式题目

**幂等导入**：同一道题重复导入会自动跳过，不会产生重复数据。

### 使用流程

1. **Tab1 导入试卷**
   - 上传文件 → 点「解析预览」查看识别结果
   - 输入试卷名称 → 点「确认入库」

2. **Tab2 题目练习**
   - 选择题目来源（全部 / 指定试卷 / 指定分组）
   - 选择题型过滤（可选）、设置题目数量
   - 点「开始练习」逐题作答
   - 完成后查看正确率和错题回顾

3. **Tab3 题库管理**
   - 按试卷浏览、分页查看题目
   - 新建自定义分组，将题目加入分组
   - 删除试卷或分组

4. **Tab4 练习记录**
   - 查看历史练习会话
   - 展开查看每次练习的错题详情

---

## 资料问答模块

### 支持的文档格式

| 格式 | 说明 |
|------|------|
| `.pdf` | 自动提取文字内容 |
| `.docx` | Word 文档 |
| `.txt` | 纯文本（UTF-8 / GBK 自动识别） |

### 使用流程

1. 上传文档（最大 50MB）
2. 等待向量化完成
3. 在对话框输入问题
4. 系统检索相关段落后由 AI 生成回答，并附上来源段落

---

## 运维命令

### Ollama 模型管理

```bash
# 查看已安装模型
ollama list

# 下载/更新模型
ollama pull qwen2.5:1.5b

# 测试模型（直接对话）
ollama run qwen2.5:1.5b

# 查看 Ollama 服务状态
systemctl status ollama
```

### 数据备份

```bash
# 手动执行备份（备份 ChromaDB 向量库）
/home/zh/medtest/scripts/backup.sh

# 查看备份文件列表
ls -lh /home/zh/medtest/data/backups/

# 自动备份：每天凌晨 3 点执行，保留最近 7 份
crontab -l
```

### 环境检查

```bash
# 运行健康检查（内存 / 目录权限 / Ollama 连通性）
cd /home/zh/medtest && venv/bin/python scripts/health_check.py
```

### 运行测试套件

```bash
cd /home/zh/medtest
venv/bin/python -m pytest tests/ -v
```

---

## 切换 LLM 后端

修改 `config/settings.py` 中的 `LLM_PROVIDER` 行，然后重启服务。

**本地 Ollama（默认）：**
```python
LLM_PROVIDER = "ollama"
OLLAMA_MODEL = "qwen2.5:1.5b"
```

**DeepSeek API（更快，需联网）：**
```python
LLM_PROVIDER = "deepseek"
DEEPSEEK_API_KEY = "sk-xxxx"
```

**智谱 GLM API：**
```python
LLM_PROVIDER = "zhipu"
ZHIPU_API_KEY = "xxxx.xxxx"
```

切换后执行 `systemctl restart medtest` 生效。

---

## 数据目录说明

```
data/
├── question_bank.db   # 题目数据库（SQLite）
├── chroma_db/         # 文档向量库（ChromaDB）
├── uploads/           # 上传的原始文件
└── backups/           # 自动备份归档
```

---

## 常见问题

**Q：上传文件后没有解析出题目？**
答：检查文件编码是否为 UTF-8，以及是否包含「答案：」行。可先用记事本保存为 UTF-8 格式再上传。

**Q：资料问答回答很慢？**
答：本地 Ollama 使用 CPU 推理，速度约 12 字/秒，属正常现象。如需更快响应可切换到 DeepSeek API。

**Q：服务重启后数据还在吗？**
答：题目数据库（SQLite）和向量库（ChromaDB）均持久化在 `data/` 目录，重启不会丢失。

**Q：如何查看错误日志？**
```bash
tail -100 /home/zh/medtest/logs/streamlit.log
```

**Q：内存不足怎么办？**
答：题目练习模块不占用额外内存（纯 SQLite）。资料问答模块需要加载 Embedding 模型（约 300MB）和 Ollama（约 1.1GB），建议关闭其他占内存的进程。
