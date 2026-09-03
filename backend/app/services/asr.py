"""STT 抽象层：Qwen3-ASR-1.7B 本地服务客户端（决策 09）+ 第三方兜底切换（P6.2）

远程服务契约（deploy/stt_server.py，开发文档 §5.1）：
  POST {ASR_BASE_URL}/v1/transcribe  (multipart: file, language)
  → {text, segments, language, duration_s, quality}

P6.2：provider 切换口 —— .env 的 ASR_PROVIDER 决定用哪个实现：
  qwen          → QwenASRProvider（本地自建，默认）
  third_party   → ThirdPartyASRProvider（第三方兼容端点，OpenAI /v1/audio/transcriptions 形态）
两个 provider 均返回转写文本；转写失败抛异常由流水线标记 quality，不静默。

注：app/core/ai/asr.py 为同构副本（P5 建），本文件为生产链路 app/services/pipeline.py 实际引用。
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


class ThirdPartyASRProvider(ASRProvider):
    """第三方兜底：OpenAI 兼容 /v1/audio/transcriptions 端点（whisper 等托管服务）。

    与 QwenASRProvider 的契约不同（multipart 的 model 字段），故独立实现。
    """

    def __init__(self, base_url: str, api_key: str = "", model: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def transcribe(self, audio_bytes: bytes, language: str | None = None) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        data: dict = {}
        if self.model:
            data["model"] = self.model
        if language:
            data["language"] = language
        resp = httpx.post(
            f"{self.base_url}/v1/audio/transcriptions",
            headers=headers,
            files={"file": ("audio.wav", audio_bytes, "audio/wav")},
            data=data,
            timeout=600,
        )
        resp.raise_for_status()
        data = resp.json()
        # OpenAI 兼容端点返回 {text: "..."}；部分实现包在 data 里
        return data.get("text", "") if isinstance(data, dict) else ""


def get_asr() -> ASRProvider:
    """按 settings.asr_provider 返回对应 provider（qwen 默认 / third_party 兜底）。"""
    if settings.asr_provider == "third_party":
        return ThirdPartyASRProvider(
            settings.asr_third_party_url,
            api_key=settings.asr_third_party_key,
            model=settings.asr_third_party_model,
        )
    return QwenASRProvider(settings.asr_base_url)
