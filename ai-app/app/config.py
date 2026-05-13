from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openrouter_api_key: str
    openrouter_model: str = "nebius/base/qwen/qwen3-32b"
    database_url: str = "postgresql+asyncpg://chat:chat@postgres:5432/chat"
    cors_origins: list[str] = ["http://localhost:3000"]

    # Conversation memory: once unsummarized messages exceed summary_threshold,
    # the oldest ones are compressed. keep_recent messages are always left verbatim.
    summary_threshold: int = 20
    keep_recent: int = 10


settings = Settings()
