from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from celery.schedules import crontab
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from config.celery import celery_app
from database.models import (
    ActivationToken,
    PasswordResetToken,
    RefreshToken,
    User,
    UserGroup,
    UserGroupEnum,
)
from security.tokens import generate_regular_token
from tasks.tokens import _task_delete_expired_token, delete_expired_tokens


@pytest.fixture
def user_groups():
    """Override the autouse seeding: its uncommitted rows would block the
    committed group insert below on the unique `name` index."""


@pytest.fixture
async def committed_tokens(engine):
    """The cleanup task opens its own connection, so the data must be committed
    (not inside the rolled-back test transaction). Removed again afterwards."""
    factory = async_sessionmaker(engine, expire_on_commit=False)
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    future = datetime.now(timezone.utc) + timedelta(hours=1)

    async with factory() as s:
        group = UserGroup(name=UserGroupEnum.USER)
        s.add(group)
        await s.flush()
        alice = User.cool_create("alice@cleanup.test", "Str0ng!Pass", group.id)
        bob = User.cool_create("bob@cleanup.test", "Str0ng!Pass", group.id)
        s.add_all([alice, bob])
        await s.flush()
        s.add_all([
            ActivationToken(user_id=alice.id, expires_at=past),
            ActivationToken(user_id=bob.id, expires_at=future),
            PasswordResetToken(user_id=alice.id, expires_at=future),
            PasswordResetToken(user_id=bob.id, expires_at=past),
            RefreshToken(user_id=alice.id, token=generate_regular_token(), expires_at=past),
            RefreshToken(user_id=alice.id, token=generate_regular_token(), expires_at=future),
        ])
        await s.commit()

    try:
        yield factory, alice.id, bob.id
    finally:
        async with factory() as s:
            await s.execute(delete(User).where(User.id.in_([alice.id, bob.id])))
            await s.execute(delete(UserGroup).where(UserGroup.id == group.id))
            await s.commit()


async def test_cleanup_deletes_only_expired_tokens(committed_tokens):
    factory, alice_id, bob_id = committed_tokens

    await _task_delete_expired_token()

    async with factory() as s:
        async def remaining(model, user_id):
            return list(await s.scalars(select(model).where(model.user_id == user_id)))

        assert await remaining(ActivationToken, alice_id) == []
        assert len(await remaining(ActivationToken, bob_id)) == 1
        assert len(await remaining(PasswordResetToken, alice_id)) == 1
        assert await remaining(PasswordResetToken, bob_id) == []
        refresh = await remaining(RefreshToken, alice_id)
        assert len(refresh) == 1
        assert refresh[0].expires_at > datetime.now(timezone.utc)
        # users themselves are untouched
        assert len(list(await s.scalars(select(User).where(User.id.in_([alice_id, bob_id]))))) == 2


def test_delete_expired_tokens_task_runs_cleanup():
    with patch("tasks.tokens._task_delete_expired_token", new_callable=AsyncMock) as cleanup:
        delete_expired_tokens()

    cleanup.assert_awaited_once()


def test_tasks_are_registered():
    celery_app.loader.import_default_modules()

    assert "tasks.tokens.delete_expired_tokens" in celery_app.tasks
    assert "tasks.emails.send_activation_email_task" in celery_app.tasks


def test_beat_schedules_hourly_token_cleanup():
    entry = celery_app.conf.beat_schedule["delete-expired-tokens"]

    assert entry["task"] == delete_expired_tokens.name
    assert entry["schedule"] == crontab(minute=0)
    assert celery_app.conf.timezone == "UTC"
