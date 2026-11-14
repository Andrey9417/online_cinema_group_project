from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, File
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image

from config.dependencies import CurrentUser, S3Client, AdminUser
from crud.accounts import register_user, activate_user, send_activation_again, login_user, refresh_token, logout_user, \
    get_profile_by_user_id, update_profile, update_profile_avatar, change_password, request_password_reset, \
    complete_password_reset, change_user_group, admin_activate_account
from database import get_db_session
from database.models import UserProfile
from exceptions.accounts import UserEmailAlreadyExist, SomethingWentWrong, InvalidActivationToken, \
    ActivationTokenExpired, AccountAlreadyActive, UserWithEmailDoesNotExist, InvalidUserCredentials, AccountNotActive, \
    InvalidJWTToken, ExpiredJWTToken, ProfileDoesNotExist, WrongOldPassword, InvalidPasswordResetToken, \
    PasswordResetTokenExpired, CannotChangeOwnGroup, UserDoesNotExist
from exceptions.storages import S3FileUploadError, S3FileDeleteError
from schemas.accounts import UserRegistrationResponseSchema, UserRegistrationRequestSchema, MessageResponseSchema, \
    UserResendActivationSchema, UserLoginResponseSchema, UserLoginRequestSchema, UserTokenRefreshRequestSchema, \
    UserTokenRefreshResponseSchema, UserLogoutRequestSchema, UserProfileResponseSchema, UserProfileUpdateSchema, \
    UserProfileAvatarSchema, PasswordChangeRequestSchema, PasswordResetRequestSchema, PasswordResetCompleteSchema, \
    AdminUserResponseSchema, UserGroupChangeRequestSchema
from storages import S3StorageInterface
from tasks.emails import send_activation_email_task, send_password_reset_email_task

router = APIRouter()
ASession = Annotated[AsyncSession, Depends(get_db_session)]


async def profile_response(profile: UserProfile, s3: S3StorageInterface):
    resp = UserProfileResponseSchema.model_validate(profile)
    if profile.avatar:
        resp.avatar = await s3.get_file_url(profile.avatar)
    return resp


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
async def get_user_profile(session: ASession, user: CurrentUser, s3: S3Client):
    if not (profile := await get_profile_by_user_id(session, user.id)):
        raise HTTPException(
            status_code=404,
            detail="Profile not found"
        )
    return await profile_response(profile, s3)


@router.patch(
    "/profile/me",
    response_model=UserProfileResponseSchema,
    status_code=status.HTTP_200_OK
)
async def update_user_profile(
        session: ASession, user: CurrentUser, prof_data: UserProfileUpdateSchema, s3: S3Client
):
    try:
        profile = await update_profile(session, user.id, prof_data)
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
    return await profile_response(profile, s3)


@router.post(
    "/profile/me/avatar",
    response_model=UserProfileResponseSchema,
    status_code=status.HTTP_200_OK
)
async def upload_profile_avatar(
        session: ASession, user: CurrentUser,
        s3: S3Client, avatar_data: Annotated[UserProfileAvatarSchema, File()]
):
    avatar = avatar_data.avatar
    image_format = Image.open(avatar.file).format
    avatar.file.seek(0)
    avatar_key = f"avatars/{user.id}/{uuid4().hex}.{image_format.lower()}"
    try:
        await s3.upload_file(avatar_key, await avatar.read(), Image.MIME[image_format])
        profile, old_avatar = await update_profile_avatar(session, user.id, avatar_key)
    except S3FileUploadError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Avatar not uploaded, try again later"
        ) from e
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
    if old_avatar:
        try:  # failed delete should not prevent new avatar upload
            await s3.delete_file(old_avatar)
        except S3FileDeleteError:
            # dunno what to do here
            ...
    return await profile_response(profile, s3)


@router.post(
    "/password/change",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK
)
async def change_user_password(
        session: ASession, user: CurrentUser, data: PasswordChangeRequestSchema
):
    try:
        await change_password(session, user, data)
    except WrongOldPassword as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        ) from e
    except SomethingWentWrong as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e
    return MessageResponseSchema(message="Password changed, log in again")


@router.post(
    "/password/reset/request",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK
)
async def request_user_password_reset(session: ASession, data: PasswordResetRequestSchema):
    try:
        user, token = await request_password_reset(session, data)
    except (UserWithEmailDoesNotExist, AccountNotActive):
        """Returns 200 cuz safety reasons"""
        return MessageResponseSchema(message="Reset token has been sent")
    except SomethingWentWrong as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e
    send_password_reset_email_task.delay(user.email, token.token)
    return MessageResponseSchema(message="Reset token has been sent")


@router.post(
    "/password/reset/complete",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK
)
async def complete_user_password_reset(session: ASession, data: PasswordResetCompleteSchema):
    try:
        await complete_password_reset(session, data)
    except (InvalidPasswordResetToken, PasswordResetTokenExpired) as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        ) from e
    except SomethingWentWrong as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e
    return MessageResponseSchema(message="Password has been reset, log in")


@router.patch(
    "/admin/users/{user_id}/group",
    response_model=AdminUserResponseSchema,
    status_code=status.HTTP_200_OK
)
async def admin_change_user_group(
        user_id: int, session: ASession, admin: AdminUser, data: UserGroupChangeRequestSchema
):
    try:
        user = await change_user_group(session, admin, user_id, data.group)
    except CannotChangeOwnGroup as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        ) from e
    except UserDoesNotExist as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        ) from e
    except SomethingWentWrong as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e
    return AdminUserResponseSchema(
        id=user.id, email=user.email, is_active=user.is_active, group=user.group.name
    )


@router.post(
    "/admin/users/{user_id}/activate",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK
)
async def admin_activate_user_account(user_id: int, session: ASession, admin: AdminUser):
    try:
        await admin_activate_account(session, user_id)
    except UserDoesNotExist as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        ) from e
    except AccountAlreadyActive as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        ) from e
    except SomethingWentWrong as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e
    return MessageResponseSchema(message="Account activated")
