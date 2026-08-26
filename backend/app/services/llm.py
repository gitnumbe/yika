import httpx

from ..config import settings


class LLMProvider:
    def chat(self, messages: list[dict]) -> str:
        raise NotImplementedError


class OpenAICompatProvider(LLMProvider):
    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def chat(self, messages: list[dict]) -> str:
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "messages": messages},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def chat(self, messages: list[dict]) -> str:
        resp = httpx.post(
            f"{self.base_url}/api/chat",
            json={"model": self.model, "messages": messages, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]


def get_llm() -> LLMProvider:
    return OpenAICompatProvider(settings.llm_base_url, settings.llm_api_key, settings.llm_model)


def get_denoise_llm() -> LLMProvider:
    return OllamaProvider(settings.ollama_base_url, settings.ollama_model)
