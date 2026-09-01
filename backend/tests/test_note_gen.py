import json

import pytest

pytestmark = pytest.mark.l1

from app.services import note_gen as ng


def test_generate_note_parses_json(monkeypatch):
    class FakeLLM:
        def chat(self, messages):
            return json.dumps({
                "summary": "s",
                "points": [{"topic": "t1", "detail": "p1"}],
                "decisions": [{"content": "d1"}],
                "todos": [{"owner": "o", "item": "x", "pending": True}],
            })

    monkeypatch.setattr(ng, "get_llm", lambda: FakeLLM())
    r = ng.generate_note("随便什么转写")
    assert r["summary"] == "s"
    assert r["points"] == [{"topic": "t1", "detail": "p1"}]
    assert r["decisions"] == [{"content": "d1"}]
    assert r["todos"] == [{"owner": "o", "item": "x", "pending": True}]
    assert r["quality"]["degraded"] is False


def test_generate_note_strips_code_fence(monkeypatch):
    class FakeLLM:
        def chat(self, messages):
            return '```json\n{"summary":"s","points":[],"decisions":[],"todos":[]}\n```'

    monkeypatch.setattr(ng, "get_llm", lambda: FakeLLM())
    r = ng.generate_note("x")
    assert r["summary"] == "s"


def test_generate_note_coerces_string_fields(monkeypatch):
    """LLM 偶发输出字符串字段 → 归一为数组（生产容错）"""
    class FakeLLM:
        def chat(self, messages):
            return json.dumps({"summary": "s", "points": "一段要点", "decisions": "一个决策", "todos": "一个待办"})

    monkeypatch.setattr(ng, "get_llm", lambda: FakeLLM())
    r = ng.generate_note("x")
    assert isinstance(r["points"], list)
    assert isinstance(r["decisions"], list)
    assert isinstance(r["todos"], list)


def test_generate_note_degrades_on_bad_json(monkeypatch):
    class FakeLLM:
        def chat(self, messages):
            return "not json at all"

    monkeypatch.setattr(ng, "get_llm", lambda: FakeLLM())
    r = ng.generate_note("x")
    assert r["quality"]["degraded"] is True
    assert r["summary"] == ""
