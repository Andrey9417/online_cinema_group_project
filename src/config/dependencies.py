from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from config.settings import Settings, settings
from database.models.accounts import User
from database.session import get_db_session
from exceptions.accounts import ExpiredJWTToken, InvalidJWTToken
from security.tokens import JWTTokenTypes, decode_jwt_token
from storages import S3StorageClient, S3StorageInterface


bearer_scheme = HTTPBearer()


def get_s3_storage_client(
        settings: Annotated[Settings, Depends(settings)]
) -> S3StorageInterface:
    return S3StorageClient(
        endpoint_url=settings.S3_STORAGE_ENDPOINT,
        access_key=settings.S3_STORAGE_ACCESS_KEY,
        secret_key=settings.S3_STORAGE_SECRET_KEY,
        bucket_name=settings.S3_BUCKET_NAME
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    token = credentials.credentials
    try:
        payload = decode_jwt_token(token, JWTTokenTypes.ACCESS)
    except (InvalidJWTToken, ExpiredJWTToken):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = int(payload["user_id"])
    stmt = (
        select(User)
        .where(User.id == user_id)
        .options(joinedload(User.group))
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user
