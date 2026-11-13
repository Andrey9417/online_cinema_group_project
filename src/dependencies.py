from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db_session
from models import User

MOCK_USER_ID = 1


async def get_current_user(db: AsyncSession = Depends(get_db_session)) -> User:
    user = await db.get(User, MOCK_USER_ID)
    if not user:
        raise HTTPException(status_code=401, detail="Mock user not found.")
    return user