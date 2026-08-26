import httpx
from app.services.asr import FunASRProvider


def test_funasr_formats_request(monkeypatch):
    def fake_post(url, **kwargs):
        assert url.endswith("/recognition")
        assert "files" in kwargs

        class R:
            def raise_for_status(self):
                pass

            def json(self):
                return {"text": "大家好"}

        return R()

    monkeypatch.setattr(httpx, "post", fake_post)
    assert FunASRProvider("http://asr").transcribe(b"fake-audio") == "大家好"
