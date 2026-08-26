import json

import pytest

pytestmark = pytest.mark.l1

from app.services import req_extract as re


def test_extract_candidates(monkeypatch):
    class FakeLLM:
        def chat(self, messages):
            return json.dumps([{"title": "自动回复", "description": "客户想要自动回复", "source_ref": "客户说想要自动回复"}])

    monkeypatch.setattr(re, "get_llm", lambda: FakeLLM())
    r = re.extract_candidates("客户说想要自动回复")
    assert len(r) == 1
    assert r[0]["title"] == "自动回复"
    assert r[0]["source_ref"] == "客户说想要自动回复"
