from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    cohort_ttl_seconds: int = 300
    log_level: str = "INFO"


settings = Settings()
