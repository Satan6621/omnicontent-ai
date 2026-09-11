from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "OmniContent AI"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    secret_key: str = "change-me-generate-a-long-random-string"
    access_token_expire_minutes: int = 60
    api_key: str = "change-me-shared-secret-for-api-clients"

    database_url: str = "sqlite:///./omnicontent_dev.db"

    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    celery_task_always_eager: bool = False

    llm_provider: str = "templates"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-haiku-latest"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"

    tts_provider: str = "auto"
    tts_voice: str = "es-MX-JorgeNeural"
    elevenlabs_api_key: str = ""

    image_provider: str = "pollinations"
    pollinations_base: str = "https://image.pollinations.ai/prompt"

    backend_cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    media_root: str = "media"
    public_media_base_url: str = "http://localhost:8000/media"
    max_upload_mb: int = 10
    video_low_memory: bool = False

    # Puente de publicación → AutoSocial
    autosocial_url: str = "http://localhost:8001"
    autosocial_publish_path: str = "/publish"
    autosocial_api_key: str = "change-me-autosocial-key"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]

    @property
    def sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def api_key_is_configured(self) -> bool:
        return bool(self.api_key) and not self.api_key.startswith("change-me")


@lru_cache
def get_settings() -> Settings:
    return Settings()
