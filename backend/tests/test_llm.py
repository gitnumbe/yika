import pytest

pytestmark = pytest.mark.l1

import httpx
from app.services.llm import OpenAICompatProvider, OllamaProvider


def test_openai_provider_formats_request(monkeypatch):
    calls = {}

    def fake_post(url, **kwargs):
        calls["url"] = url
        calls["json"] = kwargs["json"]

        class R:
            def raise_for_status(self):
                pass

            def json(self):
                return {"choices": [{"message": {"content": "hi"}}]}

        return R()

    monkeypatch.setattr(httpx, "post", fake_post)
    p = OpenAICompatProvider("http://x/v1", "sk", "qwen3-27b")
    assert p.chat([{"role": "user", "content": "你好"}]) == "hi"
    assert calls["url"] == "http://x/v1/chat/completions"
    assert calls["json"]["model"] == "qwen3-27b"


def test_ollama_provider_formats_request(monkeypatch):
    calls = {}

    def fake_post(url, **kwargs):
        calls["url"] = url
        calls["json"] = kwargs["json"]

        class R:
            def raise_for_status(self):
                pass

            def json(self):
                return {"message": {"content": "ok"}}

        return R()

    monkeypatch.setattr(httpx, "post", fake_post)
    p = OllamaProvider("http://127.0.0.1:11434", "qwen3:4b-instruct")
    assert p.chat([{"role": "user", "content": "x"}]) == "ok"
    assert calls["url"] == "http://127.0.0.1:11434/api/chat"
