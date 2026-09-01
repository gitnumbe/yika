import pytest

pytestmark = pytest.mark.l1

import httpx
from app.services.asr import QwenASRProvider


def test_qwenasr_formats_request(monkeypatch):
    def fake_post(url, **kwargs):
        assert url.endswith("/v1/transcribe")
        assert "files" in kwargs
        assert kwargs["files"]["file"][0] == "audio.wav"
        # 语言参数透传
        assert kwargs["data"]["language"] == "zh"

        class R:
            def raise_for_status(self):
                pass

            def json(self):
                return {"text": "大家好", "segments": [], "language": "zh", "duration_s": 1.0}

        return R()

    monkeypatch.setattr(httpx, "post", fake_post)
    p = QwenASRProvider("http://asr")
    assert p.transcribe(b"fake-audio", language="zh") == "大家好"


def test_qwenasr_no_language_defaults(monkeypatch):
    def fake_post(url, **kwargs):
        assert kwargs["data"]["language"] == ""

        class R:
            def raise_for_status(self):
                pass

            def json(self):
                return {"text": "ok"}

        return R()

    monkeypatch.setattr(httpx, "post", fake_post)
    assert QwenASRProvider("http://asr").transcribe(b"audio") == "ok"
