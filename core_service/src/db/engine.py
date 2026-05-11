from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.config import Settings

settings = Settings()

engine = create_async_engine(settings.db_url, echo=settings.db_echo)

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session():
    async with async_session_factory() as session:
        yield session
