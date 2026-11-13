from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from crud.accounts import register_user, activate_user, send_activation_again
from database import get_db_session
from exceptions.accounts import UserEmailAlreadyExist, SomethingWentWrong, InvalidActivationToken, \
    ActivationTokenExpired, AccountAlreadyActive, UserWithEmailDoesNotExist
from notifications.emails import send_activation_email
from schemas.accounts import UserRegistrationResponseSchema, UserRegistrationRequestSchema, MessageResponseSchema, \
    UserResendActivationSchema

router = APIRouter()
ASession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post(
    "/register",
    response_model=UserRegistrationResponseSchema,
    status_code=status.HTTP_201_CREATED
)
async def register_new_user(
        session: ASession,
        user_data: UserRegistrationRequestSchema,
        back_manager: BackgroundTasks  # will change to Celery later
):
    try:
        user, act_token = await register_user(session, user_data)
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
    back_manager.add_task(send_activation_email, user.email, act_token.token)
    return UserRegistrationResponseSchema(id=user.id, email=user.email)


@router.get(
    "/activate",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK
)
async def activate_new_user(session: ASession, token: str):
    try:
        await activate_user(session, token)
    except (InvalidActivationToken, ActivationTokenExpired, AccountAlreadyActive) as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        ) from e
    except SomethingWentWrong as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e
    return MessageResponseSchema(message="Account activation is a success")


@router.post(
    "/resend-activation",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK
)
async def send_user_activation_again(
        session: ASession,
        user_email: UserResendActivationSchema,
        back_manager: BackgroundTasks  # will change to Celery later
):
    try:
        user, token = await send_activation_again(session, user_email)
    except (UserWithEmailDoesNotExist, AccountAlreadyActive):  # log it?
        """Returns 200 cuz safety reasons"""
        return MessageResponseSchema(message="Check your email for the new activation link")
    except SomethingWentWrong as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e
    back_manager.add_task(send_activation_email, user.email, token.token)
    return MessageResponseSchema(message="Check your email for the new activation link")
