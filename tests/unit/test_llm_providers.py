"""单元测试：LLM Provider 层（mock HTTP，不依赖真实 Ollama 服务）。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from unittest.mock import patch, MagicMock
import json

from core.providers.ollama_provider import OllamaProvider


class TestOllamaProviderHealthCheck:
    def test_health_check_ok(self):
        provider = OllamaProvider()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("requests.get", return_value=mock_resp):
            assert provider.health_check() is True

    def test_health_check_server_error(self):
        provider = OllamaProvider()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        with patch("requests.get", return_value=mock_resp):
            assert provider.health_check() is False

    def test_health_check_connection_refused(self):
        provider = OllamaProvider()
        with patch("requests.get", side_effect=ConnectionError("refused")):
            assert provider.health_check() is False


class TestOllamaProviderStream:
    def _make_stream_response(self, tokens: list[str]) -> MagicMock:
        lines = []
        for i, token in enumerate(tokens):
            done = i == len(tokens) - 1
            lines.append(json.dumps({"response": token, "done": done}).encode())
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.iter_lines.return_value = lines
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    def test_stream_yields_all_tokens(self):
        provider = OllamaProvider()
        tokens = ["心脏", "有", "四个", "腔"]
        mock_resp = self._make_stream_response(tokens)
        with patch("requests.post", return_value=mock_resp):
            result = "".join(provider.generate_stream("心脏有几个腔？"))
        assert result == "心脏有四个腔"

    def test_stream_skips_empty_tokens(self):
        provider = OllamaProvider()
        lines = [
            json.dumps({"response": "回答", "done": False}).encode(),
            json.dumps({"response": "", "done": False}).encode(),
            json.dumps({"response": "内容", "done": True}).encode(),
        ]
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.iter_lines.return_value = lines
        mock_resp.raise_for_status = MagicMock()
        with patch("requests.post", return_value=mock_resp):
            result = "".join(provider.generate_stream("test"))
        assert result == "回答内容"

    def test_stream_stops_on_done(self):
        provider = OllamaProvider()
        lines = [
            json.dumps({"response": "第一段", "done": True}).encode(),
            json.dumps({"response": "不应出现", "done": False}).encode(),
        ]
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.iter_lines.return_value = lines
        mock_resp.raise_for_status = MagicMock()
        with patch("requests.post", return_value=mock_resp):
            result = "".join(provider.generate_stream("test"))
        assert result == "第一段"
        assert "不应出现" not in result
