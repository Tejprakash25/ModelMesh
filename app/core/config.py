from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "llm-gateway"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/llm_gateway"
    redis_url: str = "redis://localhost:6379/0"

    default_provider: str = "mock-primary"
    fallback_provider: str = "mock-fallback"

    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600

    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    redact_logs: bool = False
    otel_enabled: bool = False
    otel_service_name: str = "llm-gateway"

    dev_api_key: str = "sk-dev-local-key-change-me"

    # Cost estimates per 1k tokens (USD) for mock billing
    cost_per_1k_prompt_tokens: float = 0.001
    cost_per_1k_completion_tokens: float = 0.002


settings = Settings()
