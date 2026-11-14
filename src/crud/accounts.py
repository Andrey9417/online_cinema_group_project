from datetime import datetime, timezone, timedelta

from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from config.settings import settings
from database.models import User, UserGroup, UserGroupEnum, ActivationToken
from database.models.accounts import TokenBaseModel, RefreshToken, UserProfile, PasswordResetToken
from exceptions.accounts import UserEmailAlreadyExist, SomethingWentWrong, GroupDoesNotExist, InvalidActivationToken, \
    ActivationTokenExpired, AccountAlreadyActive, UserWithEmailDoesNotExist, InvalidUserCredentials, AccountNotActive, \
    InvalidJWTToken, ProfileDoesNotExist, WrongOldPassword, InvalidPasswordResetToken, PasswordResetTokenExpired, \
    CannotChangeOwnGroup, UserDoesNotExist
from schemas.accounts import UserRegistrationRequestSchema, UserResendActivationSchema, UserLoginRequestSchema, \
    UserTokenRefreshRequestSchema, UserLogoutRequestSchema, UserProfileUpdateSchema, PasswordChangeRequestSchema, \
    PasswordResetRequestSchema, PasswordResetCompleteSchema
from security.passwords import verify_password, hash_password
from security.tokens import create_access_token, create_refresh_token, decode_jwt_token, JWTTokenTypes


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(User.email == email))


async def get_user_by_id(session: AsyncSession, user_id: int, *args) -> User | None:
    return await session.scalar(select(User).options(*args).where(User.id == user_id))


async def get_profile_by_user_id(session: AsyncSession, user_id: int):
    return await session.scalar(select(UserProfile).where(UserProfile.user_id == user_id))


async def delete_token(session: AsyncSession, token: TokenBaseModel | None):
    if token is not None:
        try:
            await session.delete(token)
            await session.commit()
        except SQLAlchemyError:
            await session.rollback()
            raise SomethingWentWrong("Something went wrong, try again later")


async def register_user(
        session: AsyncSession, user_data: UserRegistrationRequestSchema
) -> tuple[User, ActivationToken]:
    if await get_user_by_email(session, user_data.email):
        raise UserEmailAlreadyExist(f"A user with this email {user_data.email} already exists.")
    if not (group := await session.scalar(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))):
        raise GroupDoesNotExist("Such group does not exist")
    user = User.cool_create(
        email=user_data.email,
        group_id=group.id,
        raw_password=user_data.raw_password
    )
    try:
        session.add(user)
        await session.flush()
        token = ActivationToken(user_id=user.id)
        session.add(token)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise UserEmailAlreadyExist(f"A user with this email {user_data.email} already exists.")
    except SQLAlchemyError:
        await session.rollback()
        raise SomethingWentWrong("Something went wrong, try again later")
    return user, token


async def activate_user(session: AsyncSession, token: str):
    if not (act_token := await session.scalar(
        select(ActivationToken)
        .options(joinedload(ActivationToken.user))
        .where(ActivationToken.token == token)
    )):
        raise InvalidActivationToken("Wrong token")
    if act_token.expires_at < datetime.now(timezone.utc):
        raise ActivationTokenExpired("Token expired")
    if act_token.user.is_active:
        await delete_token(session, act_token)
        raise AccountAlreadyActive("Account is already active")
    act_token.user.is_active = True
    await delete_token(session, act_token)


async def send_activation_again(
        session: AsyncSession, user_email: UserResendActivationSchema
) -> tuple[User, ActivationToken]:
    if not (user := await session.scalar(
        select(User)
        .options(joinedload(User.activation_token))
        .where(User.email == user_email.email)
    )):
        raise UserWithEmailDoesNotExist("User with such email does not exist")
    if user.is_active:
        await delete_token(session, user.activation_token)
        raise AccountAlreadyActive("Account is already active")
    await delete_token(session, user.activation_token)
    try:
        new_token = ActivationToken(user_id=user.id)
        session.add(new_token)
        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        raise SomethingWentWrong("Something went wrong, try again later")
    return user, new_token


async def login_user(
        session: AsyncSession, user_data: UserLoginRequestSchema
) -> tuple[str, RefreshToken]:
    user = await get_user_by_email(session, user_data.email)
    if not user or not verify_password(user_data.raw_password, user.hashed_password):
        raise InvalidUserCredentials("Invalid email or password")
    if not user.is_active:
        raise AccountNotActive("Account is not active")
    acc_token = create_access_token(user.id)
    ref_token = RefreshToken(
        user_id=user.id,
        token=create_refresh_token(user.id),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    try:
        session.add(ref_token)
        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        raise SomethingWentWrong("Something went wrong, try again later")
    return acc_token, ref_token


async def refresh_token(session: AsyncSession, token: UserTokenRefreshRequestSchema):
    payload = decode_jwt_token(token.refresh_token, JWTTokenTypes.REFRESH)
    if not await session.scalar(select(RefreshToken).where(RefreshToken.token == token.refresh_token)):
        raise InvalidJWTToken("Invalid token")
    return create_access_token(payload["user_id"])


async def logout_user(session: AsyncSession, user_data: UserLogoutRequestSchema):
    ref_token = await session.scalar(
        select(RefreshToken).where(RefreshToken.token == user_data.refresh_token)
    )
    await delete_token(session, ref_token)


async def update_profile(
        session: AsyncSession, user_id: int, prof_data: UserProfileUpdateSchema
):
    if not (profile := await get_profile_by_user_id(session, user_id)):
        raise ProfileDoesNotExist("Profile not found")
    for fi, val in prof_data.model_dump(exclude_unset=True).items():
        setattr(profile, fi, val)
    try:
        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        raise SomethingWentWrong("Something went wrong, try again later")
    return profile


async def update_profile_avatar(
        session: AsyncSession, user_id: int, avatar_key: str
):
    if not (profile := await get_profile_by_user_id(session, user_id)):
        raise ProfileDoesNotExist("Profile not found")
    old_avatar = profile.avatar
    profile.avatar = avatar_key
    try:
        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        raise SomethingWentWrong("Something went wrong, try again later")
    return profile, old_avatar


async def change_password(
        session: AsyncSession, user: User, data: PasswordChangeRequestSchema
):
    if not verify_password(data.old_password, user.hashed_password):
        raise WrongOldPassword("Old password is incorrect")
    user.hashed_password = hash_password(data.new_password)
    try:
        await session.execute(delete(RefreshToken).where(RefreshToken.user_id == user.id))
        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        raise SomethingWentWrong("Something went wrong, try again later")


async def request_password_reset(
        session: AsyncSession, data: PasswordResetRequestSchema
) -> tuple[User, PasswordResetToken]:
    if not (user := await session.scalar(
        select(User)
        .options(joinedload(User.password_reset_token))
        .where(User.email == data.email)
    )):
        raise UserWithEmailDoesNotExist("User with such email does not exist")
    if not user.is_active:
        raise AccountNotActive("Account is not active")
    try:
        if user.password_reset_token:
            await session.delete(user.password_reset_token)
            await session.flush()
        token = PasswordResetToken(
            user_id=user.id,
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
        )
        session.add(token)
        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        raise SomethingWentWrong("Something went wrong, try again later")
    return user, token


async def complete_password_reset(
        session: AsyncSession, data: PasswordResetCompleteSchema
):
    if not (reset_token := await session.scalar(
        select(PasswordResetToken)
        .options(joinedload(PasswordResetToken.user))
        .where(PasswordResetToken.token == data.token)
    )):
        raise InvalidPasswordResetToken("Invalid token")
    if reset_token.expires_at < datetime.now(timezone.utc):
        await delete_token(session, reset_token)
        raise PasswordResetTokenExpired("Token expired")
    user = reset_token.user
    user.hashed_password = hash_password(data.new_password)
    try:
        await session.delete(reset_token)
        await session.execute(delete(RefreshToken).where(RefreshToken.user_id == user.id))
        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        raise SomethingWentWrong("Something went wrong, try again later")


async def change_user_group(
        session: AsyncSession, admin: User, user_id: int, group_name: UserGroupEnum
):
    if user_id == admin.id:
        raise CannotChangeOwnGroup("You can not do that!")
    if not (user := await get_user_by_id(session, user_id, joinedload(User.group))):
        raise UserDoesNotExist("User not found")
    if not (group := await session.scalar(select(UserGroup).where(UserGroup.name == group_name))):
        raise GroupDoesNotExist("Group does not exist")
    user.group = group
    try:
        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        raise SomethingWentWrong("Something went wrong, try again later")
    return user


async def admin_activate_account(session: AsyncSession, user_id: int):
    if not (user := await get_user_by_id(session, user_id, joinedload(User.activation_token))):
        raise UserDoesNotExist("User not found")
    if user.is_active:
        raise AccountAlreadyActive("Account is already active")
    user.is_active = True
    try:
        if user.activation_token:
            await session.delete(user.activation_token)
        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        raise SomethingWentWrong("Something went wrong, try again later")
