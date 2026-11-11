from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from config.settings import settings

async_engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session