import psutil
from config.settings import MEMORY_SAFE_THRESHOLD_MB


def get_memory_usage_mb() -> float:
    return psutil.virtual_memory().used / 1024 / 1024


def get_memory_available_mb() -> float:
    return psutil.virtual_memory().available / 1024 / 1024


def assert_memory_safe(threshold_mb: int = MEMORY_SAFE_THRESHOLD_MB) -> None:
    used = get_memory_usage_mb()
    if used > threshold_mb:
        raise MemoryError(
            f"当前内存使用 {used:.0f}MB 已超过安全阈值 {threshold_mb}MB，"
            f"请等待当前任务完成后再试"
        )
