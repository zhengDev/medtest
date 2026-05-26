#!/usr/bin/env python3
"""启动前环境检查，所有检查通过后才允许启动服务。"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import psutil
from config.settings import (
    CHROMA_PERSIST_DIR, UPLOAD_DIR, LLM_PROVIDER,
    OLLAMA_BASE_URL, MEMORY_SAFE_THRESHOLD_MB,
)


def check_memory() -> bool:
    mem = psutil.virtual_memory()
    available_mb = mem.available / 1024 / 1024
    print(f"  内存可用：{available_mb:.0f}MB / 总计 {mem.total/1024/1024:.0f}MB")
    if available_mb < 800:
        print("  ✗ 可用内存不足 800MB，服务可能无法正常启动")
        return False
    print("  ✓ 内存充足")
    return True


def check_directories() -> bool:
    ok = True
    for d in [CHROMA_PERSIST_DIR, UPLOAD_DIR]:
        p = Path(d)
        try:
            p.mkdir(parents=True, exist_ok=True)
            test_file = p / ".write_test"
            test_file.touch()
            test_file.unlink()
            print(f"  ✓ 目录可写：{d}")
        except Exception as e:
            print(f"  ✗ 目录不可写：{d}（{e}）")
            ok = False
    return ok


def check_ollama() -> bool:
    if LLM_PROVIDER != "ollama":
        print(f"  跳过（当前 LLM_PROVIDER={LLM_PROVIDER}）")
        return True
    try:
        import requests
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            print(f"  ✓ Ollama 在线，已有模型：{models}")
            return True
        print(f"  ✗ Ollama 响应异常（{resp.status_code}）")
        return False
    except Exception as e:
        print(f"  ✗ Ollama 不可达：{e}")
        print("    提示：运行 'ollama serve &' 启动 Ollama 服务")
        return False


def main():
    print("=" * 50)
    print("医学知识库 启动前环境检查")
    print("=" * 50)
    results = []

    print("\n[1] 内存检查")
    results.append(check_memory())

    print("\n[2] 目录权限检查")
    results.append(check_directories())

    print("\n[3] LLM 服务检查")
    results.append(check_ollama())

    print("\n" + "=" * 50)
    # Ollama 检查（索引 2）失败不阻塞启动，题库模块不依赖 LLM
    critical = results[:2]
    if all(critical):
        print("✅ 核心检查通过，可以启动服务")
        if not results[2]:
            print("⚠️  Ollama 未启动，资料问答模块暂不可用（题库检索不受影响）")
        print("   运行：streamlit run app/main.py --server.port 8501 --server.address 0.0.0.0")
        sys.exit(0)
    else:
        print("❌ 存在未通过的核心检查项，请修复后再启动")
        sys.exit(1)


if __name__ == "__main__":
    main()
