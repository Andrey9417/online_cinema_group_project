from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from database.models import ActivationToken, User, UserGroup, UserGroupEnum

STRONG_PASSWORD = "Str0ng!Pass"


@pytest.fixture(autouse=True)
async def user_groups(db_session):
    """`create_all` builds empty tables, so seed groups the way the migration does."""
    groups = {name: UserGroup(name=name) for name in UserGroupEnum}
    db_session.add_all(groups.values())
    await db_session.commit()  # only releases a savepoint; the outer transaction is still rolled back
    return groups


@pytest.fixture(autouse=True)
def email_task():
    """Never reach Redis/SendGrid from tests; assert on `.delay` calls instead."""
    with patch("routes.accounts.send_activation_email_task", MagicMock()) as task:
        yield task


@pytest.fixture
def make_user(db_session, user_groups):
    async def _make_user(
            email: str = "user@example.com",
            is_active: bool = False,
            group: UserGroupEnum = UserGroupEnum.USER,
            token_expires_at: datetime | None = None,
            with_token: bool = True,
    ) -> tuple[User, ActivationToken | None]:
        user = User.cool_create(
            email=email, raw_password=STRONG_PASSWORD, group_id=user_groups[group].id
        )
        user.is_active = is_active
        db_session.add(user)
        await db_session.flush()
        token = None
        if with_token:
            token = ActivationToken(user_id=user.id)
            if token_expires_at is not None:
                token.expires_at = token_expires_at
            db_session.add(token)
        # commit (= release savepoint) so an app-side rollback can't wipe fixture data
        await db_session.commit()
        return user, token

    return _make_user


@pytest.fixture
def fetch(db_session):
    """Re-read rows from the DB, bypassing stale objects in the shared session."""

    async def _fetch_user(email: str) -> User | None:
        return await db_session.scalar(
            select(User).where(User.email == email).execution_options(populate_existing=True)
        )

    async def _fetch_tokens(user_id: int) -> list[ActivationToken]:
        return list(await db_session.scalars(
            select(ActivationToken)
            .where(ActivationToken.user_id == user_id)
            .execution_options(populate_existing=True)
        ))

    return SimpleNamespace(user=_fetch_user, tokens=_fetch_tokens)
