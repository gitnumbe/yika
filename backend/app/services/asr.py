"""STT 抽象层：Qwen3-ASR-1.7B 本地服务客户端（决策 09）

远程服务契约（deploy/stt_server.py，开发文档 §5.1）：
  POST {ASR_BASE_URL}/v1/transcribe  (multipart: file, language)
  → {text, segments, language, duration_s, quality}
"""
import httpx

from ..config import settings


class ASRProvider:
    def transcribe(self, audio_bytes: bytes, language: str | None = None) -> str:
        raise NotImplementedError


class QwenASRProvider(ASRProvider):
    """调用本地 STT 服务（Qwen3-ASR-1.7B）"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def transcribe(self, audio_bytes: bytes, language: str | None = None) -> str:
        resp = httpx.post(
            f"{self.base_url}/v1/transcribe",
            files={"file": ("audio.wav", audio_bytes, "audio/wav")},
            data={"language": language or ""},
            timeout=600,  # 长音频转写可能耗时
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("text", "")


def get_asr() -> ASRProvider:
    return QwenASRProvider(settings.asr_base_url)
