import json

import pytest

pytestmark = pytest.mark.l1

from app.services import req_extract as re


def test_extract_candidates(monkeypatch):
    class FakeLLM:
        def chat(self, messages):
            return json.dumps([
                {"title": "自动回复", "description": "客户想要自动回复", "source_ref": "客户说想要自动回复", "confidence": 0.8, "reason": "客户明确提及"}
            ])

    monkeypatch.setattr(re, "get_llm", lambda: FakeLLM())
    r = re.extract_candidates("客户说想要自动回复")
    assert len(r["candidates"]) == 1
    assert r["candidates"][0]["title"] == "自动回复"
    assert r["candidates"][0]["source_ref"] == "客户说想要自动回复"
    assert r["quality"]["degraded"] is False


def test_extract_skips_titlesless(monkeypatch):
    class FakeLLM:
        def chat(self, messages):
            return json.dumps([
                {"title": "", "description": "没标题"},
                {"title": "有效需求", "description": "ok"},
            ])

    monkeypatch.setattr(re, "get_llm", lambda: FakeLLM())
    r = re.extract_candidates("x")
    assert len(r["candidates"]) == 1
    assert r["candidates"][0]["title"] == "有效需求"


def test_extract_degrades_on_bad_json(monkeypatch):
    class FakeLLM:
        def chat(self, messages):
            return "不是JSON"

    monkeypatch.setattr(re, "get_llm", lambda: FakeLLM())
    r = re.extract_candidates("x")
    assert r["candidates"] == []
    assert r["quality"]["degraded"] is True
