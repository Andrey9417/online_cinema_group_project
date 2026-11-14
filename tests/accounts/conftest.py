from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from config.dependencies import get_s3_storage_client
from database.models import ActivationToken, User, UserGroup, UserGroupEnum
from database.models.accounts import PasswordResetToken, RefreshToken, UserProfile
from main import app
from security.tokens import create_access_token
from storages import S3StorageInterface

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


@pytest.fixture(autouse=True)
def reset_email_task():
    with patch("routes.accounts.send_password_reset_email_task", MagicMock()) as task:
        yield task


@pytest.fixture
def fake_s3(client):
    """Replaces the S3 client for routes; `client` first so its teardown clears the override."""
    s3 = AsyncMock(spec=S3StorageInterface)
    s3.get_file_url.side_effect = lambda key: f"http://s3.test/bucket/{key}"
    app.dependency_overrides[get_s3_storage_client] = lambda: s3
    return s3


@pytest.fixture
def auth_headers():
    def _auth_headers(user: User) -> dict[str, str]:
        return {"Authorization": f"Bearer {create_access_token(user.id)}"}

    return _auth_headers


@pytest.fixture
def login(client):
    async def _login(email: str = "user@example.com", password: str = STRONG_PASSWORD):
        return await client.post(
            "/api/v1/accounts/login", json={"email": email, "raw_password": password}
        )

    return _login


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

    async def _fetch_rows(model, user_id: int) -> list:
        return list(await db_session.scalars(
            select(model)
            .where(model.user_id == user_id)
            .execution_options(populate_existing=True)
        ))

    async def _fetch_tokens(user_id: int) -> list[ActivationToken]:
        return await _fetch_rows(ActivationToken, user_id)

    async def _fetch_refresh_tokens(user_id: int) -> list[RefreshToken]:
        return await _fetch_rows(RefreshToken, user_id)

    async def _fetch_reset_tokens(user_id: int) -> list[PasswordResetToken]:
        return await _fetch_rows(PasswordResetToken, user_id)

    async def _fetch_profile(user_id: int) -> UserProfile | None:
        rows = await _fetch_rows(UserProfile, user_id)
        return rows[0] if rows else None

    return SimpleNamespace(
        user=_fetch_user,
        tokens=_fetch_tokens,
        refresh_tokens=_fetch_refresh_tokens,
        reset_tokens=_fetch_reset_tokens,
        profile=_fetch_profile,
    )
