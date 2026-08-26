from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "qwen3-27b"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:4b-instruct"
    asr_base_url: str = ""
    database_url: str = "sqlite:///./app.db"
    secret_key: str = "change-me"


settings = Settings()
