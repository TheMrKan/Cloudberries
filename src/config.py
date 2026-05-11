from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_url: str = (
        "postgresql+asyncpg://cloudberries:cloudberries@localhost:5432/cloudberries"
    )
    db_echo: bool = False
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = "cloudberries-secret-key"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_project_id: str | None = None

    model_config = {"env_file": ".env"}
