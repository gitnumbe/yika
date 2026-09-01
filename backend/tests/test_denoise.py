import json

import pytest

pytestmark = pytest.mark.l1

from app.services import denoise as d


def test_denoise_calls_llm_and_parses(monkeypatch):
    class FakeLLM:
        def chat(self, messages):
            assert "删除寒暄" in messages[0]["content"]
            return json.dumps([
                {"sentence": "嗯，大家好", "keep": False, "reason": "寒暄"},
                {"sentence": "我们开始讨论需求", "keep": True, "reason": "干货"},
            ])

    monkeypatch.setattr(d, "get_denoise_llm", lambda: FakeLLM())
    r = d.denoise_transcript("嗯，大家好\n我们开始讨论需求")
    assert r["text"] == "我们开始讨论需求"
    assert r["quality"]["rules_fallback"] is False


def test_denoise_falls_back_to_rules_on_llm_failure(monkeypatch):
    class BadLLM:
        def chat(self, messages):
            raise RuntimeError("boom")

    monkeypatch.setattr(d, "get_denoise_llm", lambda: BadLLM())
    r = d.denoise_transcript("嗯嗯\n好的好的\n我们开始讨论需求")
    # LLM 挂了 → 规则兜底：纯寒暄行被滤，干货保留（规则保守：只滤明显废话）
    assert "我们开始讨论需求" in r["text"]
    assert r["quality"]["rules_fallback"] is True


def test_denoise_empty_transcript():
    r = d.denoise_transcript("")
    assert r["text"] == ""
    assert r["quality"]["note"] == "empty transcript"
