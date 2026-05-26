from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# ── Embedding ──────────────────────────────────────────────
EMBEDDING_PROVIDER = "e5"                         # 切换: "e5" | 未来可加 "bge_m3"
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
EMBEDDING_DEVICE = "cpu"
EMBEDDING_BATCH_SIZE = 16

# ── LLM ────────────────────────────────────────────────────
LLM_PROVIDER = "ollama"                           # 切换: "ollama" | "deepseek" | "zhipu"
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:1.5b"
OLLAMA_TIMEOUT = 300                              # 秒，CPU推理较慢

DEEPSEEK_API_KEY = ""                             # 使用 DeepSeek 时填入
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"

ZHIPU_API_KEY = ""                                # 使用智谱 GLM 时填入
ZHIPU_MODEL = "glm-4-flash"

# ── Vector Store ────────────────────────────────────────────
VECTOR_STORE_PROVIDER = "chroma"                  # 切换: "chroma" | 未来可加 "qdrant"
CHROMA_PERSIST_DIR = str(BASE_DIR / "data" / "chroma_db")
QUESTIONS_COLLECTION = "questions"
DOCUMENTS_COLLECTION = "documents"

# ── Text Splitting ──────────────────────────────────────────
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# ── Retrieval ───────────────────────────────────────────────
RETRIEVAL_TOP_K = 5
RETRIEVAL_SCORE_THRESHOLD = 0.3                   # cosine distance，低于此值丢弃

# ── Memory Guard ────────────────────────────────────────────
MEMORY_SAFE_THRESHOLD_MB = 2800                   # 无Swap环境保护阈值

# ── Upload ──────────────────────────────────────────────────
UPLOAD_DIR = str(BASE_DIR / "data" / "uploads")
MAX_UPLOAD_MB = 50
SUPPORTED_DOC_EXTENSIONS = [".pdf", ".docx", ".txt"]
SUPPORTED_QUESTION_EXTENSIONS = [".pdf", ".txt", ".csv", ".json"]
