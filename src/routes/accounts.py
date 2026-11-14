from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import CurrentUser
from crud.accounts import register_user, activate_user, send_activation_again, login_user, refresh_token, logout_user, \
    get_profile_by_user_id, update_profile
from database import get_db_session
from exceptions.accounts import UserEmailAlreadyExist, SomethingWentWrong, InvalidActivationToken, \
    ActivationTokenExpired, AccountAlreadyActive, UserWithEmailDoesNotExist, InvalidUserCredentials, AccountNotActive, \
    InvalidJWTToken, ExpiredJWTToken, ProfileDoesNotExist
from schemas.accounts import UserRegistrationResponseSchema, UserRegistrationRequestSchema, MessageResponseSchema, \
    UserResendActivationSchema, UserLoginResponseSchema, UserLoginRequestSchema, UserTokenRefreshRequestSchema, \
    UserTokenRefreshResponseSchema, UserLogoutRequestSchema, UserProfileResponseSchema, UserProfileUpdateSchema
from tasks.emails import send_activation_email_task

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
    send_activation_email_task.delay(user.email, act_token.token)
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
    send_activation_email_task.delay(user.email, token.token)
    return MessageResponseSchema(message="Check your email for the new activation link")


@router.post(
    "/login",
    response_model=UserLoginResponseSchema,
    status_code=status.HTTP_201_CREATED
)
async def good_login_user(session: ASession, user_data: UserLoginRequestSchema):
    try:
        acc_token, ref_token = await login_user(session, user_data)
    except InvalidUserCredentials as e:
        raise HTTPException(
            status_code=401,
            detail=str(e)
        ) from e
    except AccountNotActive as e:
        raise HTTPException(
            status_code=403,
            detail=str(e)
        ) from e
    except SomethingWentWrong as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e
    return UserLoginResponseSchema(access_token=acc_token, refresh_token=ref_token.token)


@router.post(
    "/refresh-token",
    response_model=UserTokenRefreshResponseSchema,
    status_code=status.HTTP_200_OK
)
async def good_refresh_token(session: ASession, token: UserTokenRefreshRequestSchema):
    try:
        acc_token = await refresh_token(session, token)
    except (InvalidJWTToken, ExpiredJWTToken) as e:
        raise HTTPException(
            status_code=401,
            detail=str(e)
        ) from e
    return UserTokenRefreshResponseSchema(access_token=acc_token)


@router.post(
    "/logout",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK
)
async def good_logout_user(session: ASession, user_data: UserLogoutRequestSchema):
    try:
        await logout_user(session, user_data)
    except SomethingWentWrong as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e
    return MessageResponseSchema(message="Come back =(")


@router.get(
    "/profile/me",
    response_model=UserProfileResponseSchema,
    status_code=status.HTTP_200_OK
)
async def get_user_profile(session: ASession, user: CurrentUser):
    if not (profile := await get_profile_by_user_id(session, user.id)):
        raise HTTPException(
            status_code=404,
            detail="Profile not found"
        )
    return profile


@router.patch(
    "/profile/me",
    response_model=UserProfileResponseSchema,
    status_code=status.HTTP_200_OK
)
async def update_user_profile(
        session: ASession, user: CurrentUser, prof_data: UserProfileUpdateSchema
):
    try:
        return await update_profile(session, user.id, prof_data)
    except ProfileDoesNotExist as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        ) from e
    except SomethingWentWrong as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e
