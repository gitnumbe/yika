import pytest

pytestmark = pytest.mark.l1

import httpx
from app.services.tts import DotsTTSProvider


def test_dotstts_formats_request(monkeypatch):
    calls = {}

    def fake_post(url, **kwargs):
        calls["url"] = url
        calls["json"] = kwargs["json"]

        class R:
            def raise_for_status(self):
                pass

            @property
            def content(self):
                return b"RIFF....wav"

        return R()

    monkeypatch.setattr(httpx, "post", fake_post)
    audio = DotsTTSProvider("http://tts").speak("大家好", voice_ref="default")
    assert audio[:4] == b"RIFF"
    assert calls["url"] == "http://tts/v1/speak"
    assert calls["json"]["text"] == "大家好"
    assert calls["json"]["voice_ref"] == "default"


def test_dotstts_timeout_raises(monkeypatch):
    import httpx as hx

    def fake_post(url, **kwargs):
        raise hx.TimeoutException("timeout")

    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(hx.TimeoutException):
        DotsTTSProvider("http://tts").speak("hi")
