import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from unittest.mock import patch
from core.utils.memory_guard import assert_memory_safe, get_memory_usage_mb


def test_assert_memory_safe_passes_when_under_threshold():
    with patch("psutil.virtual_memory") as mock_mem:
        mock_mem.return_value.used = 1000 * 1024 * 1024  # 1000MB
        assert_memory_safe(threshold_mb=2800)  # 不应抛出异常


def test_assert_memory_safe_raises_when_over_threshold():
    import pytest
    with patch("psutil.virtual_memory") as mock_mem:
        mock_mem.return_value.used = 3000 * 1024 * 1024  # 3000MB
        with pytest.raises(MemoryError, match="安全阈值"):
            assert_memory_safe(threshold_mb=2800)


def test_get_memory_usage_mb_returns_positive():
    result = get_memory_usage_mb()
    assert result > 0
