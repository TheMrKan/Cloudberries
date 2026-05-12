from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    db_url: str = "postgresql+asyncpg://cloudberries:cloudberries@localhost:5432/cloudberries"
    db_echo: bool = False

    # Redis (for Celery broker and result backend)
    redis_url: str = "redis://localhost:6379/0"

    # OpenAI / LLM API
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    # Scraper settings
    cloud_docs_folder: str = "cloud_docs"
    markdown_line_limit: int = 150

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")