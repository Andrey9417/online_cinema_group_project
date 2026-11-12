from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from crud.accounts import register_user
from database import get_db_session
from schemas.accounts import UserRegistrationResponseSchema, UserRegistrationRequestSchema

router = APIRouter()
ASession = Annotated[AsyncSession, Depends(get_db_session)]

@router.post("/register", response_model=UserRegistrationResponseSchema)
async def register_new_user(session: ASession, user_data: UserRegistrationRequestSchema):
    user, act_token = await register_user(session, user_data) # TODO: send email
    return UserRegistrationResponseSchema(id=user.id, email=user.email)
