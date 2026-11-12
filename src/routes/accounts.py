from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from crud.accounts import register_user
from database import get_db_session
from exceptions.accounts import UserEmailAlreadyExist, SomethingWentWrong
from schemas.accounts import UserRegistrationResponseSchema, UserRegistrationRequestSchema

router = APIRouter()
ASession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post(
    "/register",
    response_model=UserRegistrationResponseSchema,
    status_code=status.HTTP_201_CREATED
)
async def register_new_user(session: ASession, user_data: UserRegistrationRequestSchema):
    try:
        user, act_token = await register_user(session, user_data)  # TODO: send email
    except UserEmailAlreadyExist as e:
        raise HTTPException(
            status_code=409,
            detail=str(e)
        ) from e
    except SomethingWentWrong as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e
    return UserRegistrationResponseSchema(id=user.id, email=user.email)
