from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import settings


# Convert sync URL to async
_pg_url = settings.postgres_url
if _pg_url.startswith("postgresql://"):
    _pg_url = _pg_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(_pg_url, echo=False, pool_size=10, max_overflow=20)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """Dependency for FastAPI endpoints."""
    async with async_session() as session:
        yield session
