from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database.models import User, UserGroup, UserGroupEnum, ActivationToken
from database.models.accounts import TokenBaseModel
from exceptions.accounts import UserEmailAlreadyExist, SomethingWentWrong, GroupDoesNotExist, InvalidActivationToken, \
    ActivationTokenExpired, AccountAlreadyActive, UserWithEmailDoesNotExist
from schemas.accounts import UserRegistrationRequestSchema, UserResendActivationSchema


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(User.email == email))


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
