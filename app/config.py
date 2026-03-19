"""Application configuration."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment."""

    database_url: str = "postgresql://eval_user:eval_pass@localhost:5432/eval_db"
    redis_url: str = "redis://localhost:6379/0"
    openai_api_key: str = ""

    # Evaluation thresholds
    latency_warning_ms: int = 2000  # single tool + avg per assistant turn
    coherence_turn_threshold: int = 5

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
