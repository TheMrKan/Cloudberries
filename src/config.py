from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_url: str = (
        "postgresql+asyncpg://cloudberries:cloudberries@localhost:5432/cloudberries"
    )
    db_echo: bool = False
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = "cloudberries-secret-key"

    model_config = {"env_file": ".env"}
