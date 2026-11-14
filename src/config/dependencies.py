from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from config.settings import Settings, settings
from database.models.accounts import User, UserGroupEnum
from database.session import get_db_session
from exceptions.accounts import ExpiredJWTToken, InvalidJWTToken
from security.tokens import JWTTokenTypes, decode_jwt_token
from storages import S3StorageClient, S3StorageInterface


bearer_scheme = HTTPBearer()
GLVL = {
    UserGroupEnum.USER: 100,
    UserGroupEnum.MODERATOR: 200,
    UserGroupEnum.ADMIN: 300,
}


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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )
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
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active",
        )

    return user


def require_group(min_g: UserGroupEnum):
    async def check_the_heck(user: User = Depends(get_current_user)):
        if GLVL[user.group.name] < GLVL[min_g]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You have no rights here!",
            )
        return user
    return check_the_heck


################ shortcuts for routs ########################
CurrentUser = Annotated[User, Depends(get_current_user)]
ModeratorUser = Annotated[User, Depends(require_group(UserGroupEnum.MODERATOR))]
AdminUser = Annotated[User, Depends(require_group(UserGroupEnum.ADMIN))]
#############################################################


async def require_moderator(current_user: User = Depends(get_current_user)) -> User:
    if current_user.group.name not in (UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN):
        raise HTTPException(status_code=403, detail="Not enough permissions.")
    return current_user
