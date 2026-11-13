from typing import AsyncGenerator
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from config.settings import settings
from models import User

async_engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


MOCK_USER_ID = 1


async def get_current_user(db: AsyncSession = Depends(get_db_session)) -> User:
    user = await db.get(User, MOCK_USER_ID)
    if not user:
        raise HTTPException(status_code=401, detail="Mock user not found.")
    return user