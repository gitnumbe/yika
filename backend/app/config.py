from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # 大模型（OpenAI 兼容·实例以 .env 为准，基准见开发文档 §4.0）
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "deepseek-v4-flash-vision-exp"
    # 去噪小模型（Ollama）
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:4b-instruct"
    # STT（Qwen3-ASR·决策 09）
    asr_base_url: str = "http://127.0.0.1:8051"
    # TTS（dots.tts·决策 09）
    tts_base_url: str = "http://127.0.0.1:8052"
    database_url: str = "sqlite:///./app.db"
    secret_key: str = "change-me"
    # CORS 白名单（逗号分隔；生产必配）
    cors_origins: str = ""


settings = Settings()
