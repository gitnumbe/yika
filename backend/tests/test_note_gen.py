import json

import pytest

pytestmark = pytest.mark.l1

from app.services import note_gen as ng


def test_generate_note_parses_json(monkeypatch):
    class FakeLLM:
        def chat(self, messages):
            return json.dumps({"summary": "s", "points": "p", "decisions": "d", "todos": "t"})

    monkeypatch.setattr(ng, "get_llm", lambda: FakeLLM())
    r = ng.generate_note("随便什么转写")
    assert r == {"summary": "s", "points": "p", "decisions": "d", "todos": "t"}


def test_generate_note_strips_code_fence(monkeypatch):
    class FakeLLM:
        def chat(self, messages):
            return '```json\n{"summary":"s","points":"p","decisions":"d","todos":"t"}\n```'

    monkeypatch.setattr(ng, "get_llm", lambda: FakeLLM())
    r = ng.generate_note("x")
    assert r["summary"] == "s"
