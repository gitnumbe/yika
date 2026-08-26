import pytest

pytestmark = pytest.mark.l1

from app.services import denoise as d


def test_denoise_calls_llm(monkeypatch):
    class FakeLLM:
        def chat(self, messages):
            assert "删除寒暄" in messages[0]["content"]
            return "清洗后"

    monkeypatch.setattr(d, "get_denoise_llm", lambda: FakeLLM())
    assert d.denoise_transcript("嗯，大家好，我们开始吧") == "清洗后"
