#!/usr/bin/env python3
"""Ollama 推理性能基准测试，输出 token/秒、内存峰值、回答质量供决策参考。"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import psutil
from core.providers.ollama_provider import OllamaProvider

TEST_PROMPTS = [
    "心脏有几个腔？分别是什么？",
    "高血压的诊断标准是什么？",
    "阿司匹林的主要适应症有哪些？",
    "简述肺炎的常见病原体。",
    "什么是糖尿病酮症酸中毒？",
]


def run_benchmark():
    provider = OllamaProvider()

    print("=" * 60)
    print("Ollama LLM 性能基准测试")
    print("=" * 60)

    if not provider.health_check():
        print("✗ Ollama 服务未启动，请先运行：ollama serve")
        sys.exit(1)

    mem_before = psutil.virtual_memory().used / 1024 / 1024
    print(f"\n基线内存使用：{mem_before:.0f}MB")

    total_tokens = 0
    total_time = 0.0

    for i, prompt in enumerate(TEST_PROMPTS, 1):
        print(f"\n[问题 {i}] {prompt}")
        print("回答：", end="", flush=True)

        start = time.time()
        tokens = []
        for chunk in provider.generate_stream(prompt):
            tokens.append(chunk)
            print(chunk, end="", flush=True)
        elapsed = time.time() - start
        print()

        token_count = len("".join(tokens))
        tps = token_count / elapsed if elapsed > 0 else 0
        total_tokens += token_count
        total_time += elapsed
        print(f"  ⏱ 耗时：{elapsed:.1f}秒  速率：{tps:.1f} 字符/秒")

    mem_after = psutil.virtual_memory().used / 1024 / 1024
    avg_tps = total_tokens / total_time if total_time > 0 else 0

    print("\n" + "=" * 60)
    print("测试结论")
    print("=" * 60)
    print(f"平均速率：{avg_tps:.1f} 字符/秒")
    print(f"Ollama 内存增量：{mem_after - mem_before:.0f}MB")
    print(f"当前总内存使用：{mem_after:.0f}MB / {psutil.virtual_memory().total/1024/1024:.0f}MB")
    print()
    if avg_tps >= 3:
        print("✅ 推理速度可接受，建议使用本地 Ollama")
    else:
        print("⚠️  推理速度较慢（< 3字符/秒），建议切换到 DeepSeek/GLM API")
        print("   修改 config/settings.py 中：LLM_PROVIDER = 'deepseek'")


if __name__ == "__main__":
    run_benchmark()
