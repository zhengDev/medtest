#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "======================================"
echo "医学知识库 一键安装脚本"
echo "======================================"

# 1. git
echo ""
echo "[1/5] 检查 git..."
if ! command -v git &>/dev/null; then
    sudo dnf install git -y
fi
echo "  ✓ git 已就绪"

# 2. Python venv
echo ""
echo "[2/5] 创建 Python 虚拟环境..."
cd "$PROJECT_DIR"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip -q
echo "  ✓ 虚拟环境已就绪"

# 3. 依赖包（分步安装防止 OOM）
echo ""
echo "[3/5] 安装 Python 依赖（较耗时，请勿中断）..."
pip install psutil requests -q
pip install pymupdf python-docx -q
pip install "chromadb==0.4.24" -q
pip install "sentence-transformers>=2.7.0" -q  # 会拉取 torch CPU 版本，约 800MB
pip install "streamlit>=1.35.0" pytest -q
echo "  ✓ Python 依赖安装完成"

# 4. Ollama（可选）
echo ""
echo "[4/5] 安装 Ollama（可选，第二阶段需要）..."
read -p "  是否现在安装 Ollama？[y/N] " install_ollama
if [ "$install_ollama" = "y" ] || [ "$install_ollama" = "Y" ]; then
    curl -fsSL https://ollama.com/install.sh | sh
    echo "  ✓ Ollama 安装完成"
    read -p "  是否立即下载 qwen2.5:1.5b 模型（约 935MB）？[y/N] " pull_model
    if [ "$pull_model" = "y" ] || [ "$pull_model" = "Y" ]; then
        ollama pull qwen2.5:1.5b
        echo "  ✓ 模型下载完成"
    fi
else
    echo "  跳过 Ollama 安装（可稍后手动安装）"
fi

# 5. 创建数据目录
echo ""
echo "[5/5] 初始化数据目录..."
mkdir -p "$PROJECT_DIR/data/chroma_db"
mkdir -p "$PROJECT_DIR/data/uploads"
mkdir -p "$PROJECT_DIR/data/backups"
chmod +x "$PROJECT_DIR/scripts/"*.sh 2>/dev/null || true
echo "  ✓ 数据目录已创建"

echo ""
echo "======================================"
echo "✅ 安装完成！"
echo ""
echo "启动前检查："
echo "  source venv/bin/activate"
echo "  python scripts/health_check.py"
echo ""
echo "启动服务："
echo "  streamlit run app/main.py --server.port 8501 --server.address 0.0.0.0"
echo "======================================"
