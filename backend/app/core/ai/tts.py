"""TTS 抽象层：dots.tts-mf 本地服务客户端（决策 09，v2.0 新增）

远程服务契约（deploy/tts_server.py，开发文档 §5.6）：
  POST {TTS_BASE_URL}/v1/speak  (json: text, voice_ref, emotion)
  → audio/wav 字节流
"""
import httpx

from ...config import settings


class TTSProvider:
    def speak(self, text: str, voice_ref: str = "default") -> bytes:
        raise NotImplementedError


class DotsTTSProvider(TTSProvider):
    """调用本地 TTS 服务（dots.tts-mf）"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def speak(self, text: str, voice_ref: str = "default") -> bytes:
        resp = httpx.post(
            f"{self.base_url}/v1/speak",
            json={"text": text, "voice_ref": voice_ref, "emotion": "neutral"},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.content  # audio/wav


def get_tts() -> TTSProvider:
    return DotsTTSProvider(settings.tts_base_url)
