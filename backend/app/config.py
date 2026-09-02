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
    # 文件存储根目录（录音/TTS 产物）
    storage_root: str = "storage"
    # P0.3 种子数据（.env 可覆盖；未配置用默认，仅开发/首启用）
    seed_admin_username: str = "admin"
    seed_admin_password: str = "admin123"
    seed_group_name: str = "技术组"
    # P0.5 日志级别（.env 可覆盖）
    log_level: str = "INFO"
    # P1.1 统一登录：共享 Cookie 域（iframe 子系统共享登录态，需同父域）
    cookie_domain: str = ""          # 例如 .yourdomain.com；留空=当前域(开发)
    cookie_secure: bool = False       # 生产 HTTPS 置 True
    cookie_name: str = "yika_access"
    # P1.6 事件总线：RabbitMQ topic 广播
    rabbitmq_url: str = "amqp://guest:guest@127.0.0.1:5672/"
    rabbitmq_exchange: str = "yika.events"


settings = Settings()
