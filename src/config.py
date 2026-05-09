from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_url: str = (
        "postgresql+asyncpg://cloudberries:cloudberries@localhost:5432/cloudberries"
    )
    db_echo: bool = False

    model_config = {"env_file": ".env"}
