import httpx

from ..config import settings


class ASRProvider:
    def transcribe(self, audio_bytes: bytes) -> str:
        raise NotImplementedError


class FunASRProvider(ASRProvider):
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def transcribe(self, audio_bytes: bytes) -> str:
        resp = httpx.post(
            f"{self.base_url}/recognition",
            files={"file": ("audio.wav", audio_bytes, "audio/wav")},
            timeout=300,
        )
        resp.raise_for_status()
        data = resp.json()
        # FunASR 返回结构视部署而定；此处约定返回 {"text": "..."}
        return data.get("text", "")


def get_asr() -> ASRProvider:
    return FunASRProvider(settings.asr_base_url)
