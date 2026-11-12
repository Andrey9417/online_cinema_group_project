from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, UserGroup, UserGroupEnum, ActivationToken
from exceptions.accounts import UserEmailAlreadyExist, SomethingWentWrong, GroupDoesNotExist
from schemas.accounts import UserRegistrationRequestSchema


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(User.email == email))


async def register_user(
        session: AsyncSession, user_data: UserRegistrationRequestSchema
) -> tuple[User, ActivationToken]:
    if await get_user_by_email(session, user_data.email):
        raise UserEmailAlreadyExist(f"A user with this email {user_data.email} already exists.")
    group = await session.scalar(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))
    if not group:
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
