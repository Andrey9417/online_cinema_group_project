from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from celery.schedules import crontab
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from config.celery import celery_app
from config.settings import settings
from database.models import (
    ActivationToken,
    PasswordResetToken,
    RefreshToken,
    User,
    UserGroup,
    UserGroupEnum,
)
from database.models.accounts import UserProfile
from exceptions.storages import S3FileListError
from security.tokens import generate_regular_token
from storages import S3StorageInterface
from tasks.avatars import _task_delete_orphaned_avatars, delete_orphaned_avatars
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
    assert "tasks.emails.send_password_reset_email_task" in celery_app.tasks
    assert "tasks.avatars.delete_orphaned_avatars" in celery_app.tasks


def test_beat_schedules_hourly_token_cleanup():
    entry = celery_app.conf.beat_schedule["delete-expired-tokens"]

    assert entry["task"] == delete_expired_tokens.name
    assert entry["schedule"] == crontab(minute=0)
    assert celery_app.conf.timezone == "UTC"


# Orphaned avatars

REFERENCED = "avatars/1/referenced.png"
ORPHAN = "avatars/2/orphan.png"


@pytest.fixture
async def committed_avatars(engine):
    """Like `committed_tokens`: the task reads profiles through its own engine.
    alice's profile references REFERENCED, bob's has no avatar."""
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as s:
        group = UserGroup(name=UserGroupEnum.USER)
        s.add(group)
        await s.flush()
        alice = User.cool_create("alice@avatars.test", "Str0ng!Pass", group.id)
        bob = User.cool_create("bob@avatars.test", "Str0ng!Pass", group.id)
        s.add_all([alice, bob])
        await s.flush()
        await s.execute(
            update(UserProfile).where(UserProfile.user_id == alice.id).values(avatar=REFERENCED)
        )
        await s.commit()

    try:
        yield
    finally:
        async with factory() as s:
            await s.execute(delete(User).where(User.id.in_([alice.id, bob.id])))
            await s.execute(delete(UserGroup).where(UserGroup.id == group.id))
            await s.commit()


@pytest.fixture
def avatar_s3():
    s3 = AsyncMock(spec=S3StorageInterface)
    with patch("tasks.avatars.get_s3_storage_client", return_value=s3):
        yield s3


def ago(minutes: float) -> datetime:
    return datetime.now(timezone.utc) - timedelta(minutes=minutes)


GRACE = settings.AVATAR_ORPHAN_GRACE_MINUTES


async def test_avatar_cleanup_deletes_only_old_orphans(committed_avatars, avatar_s3):
    avatar_s3.list_files.return_value = [
        (REFERENCED, ago(GRACE * 10)),         # in use -> kept, however old
        (ORPHAN, ago(GRACE + 1)),              # unreferenced, past grace -> deleted
        ("avatars/3/fresh.png", ago(GRACE - 1)),  # unreferenced but maybe not committed yet -> kept
    ]

    await _task_delete_orphaned_avatars()

    avatar_s3.list_files.assert_awaited_once_with("avatars/")
    avatar_s3.delete_files.assert_awaited_once_with([ORPHAN])


async def test_avatar_cleanup_deletes_avatar_of_deleted_user(committed_avatars, avatar_s3, engine):
    """User deleted -> profile cascades away -> its avatar key becomes an orphan."""
    async with async_sessionmaker(engine)() as s:
        await s.execute(delete(User).where(User.email == "alice@avatars.test"))
        await s.commit()
    avatar_s3.list_files.return_value = [(REFERENCED, ago(GRACE + 1))]

    await _task_delete_orphaned_avatars()

    avatar_s3.delete_files.assert_awaited_once_with([REFERENCED])


async def test_avatar_cleanup_nothing_to_delete(committed_avatars, avatar_s3):
    avatar_s3.list_files.return_value = [(REFERENCED, ago(GRACE + 1))]

    await _task_delete_orphaned_avatars()

    # calling delete_files([]) is fine (it makes no storage call); deleting anything is not
    for call in avatar_s3.delete_files.await_args_list:
        assert call.args == ([],)


async def test_avatar_cleanup_list_error_deletes_nothing(committed_avatars, avatar_s3):
    avatar_s3.list_files.side_effect = S3FileListError("boom")

    with pytest.raises(S3FileListError):
        await _task_delete_orphaned_avatars()

    avatar_s3.delete_files.assert_not_called()


def test_delete_orphaned_avatars_task_runs_cleanup():
    with patch("tasks.avatars._task_delete_orphaned_avatars", new_callable=AsyncMock) as cleanup:
        delete_orphaned_avatars()

    cleanup.assert_awaited_once()


def test_beat_schedules_daily_avatar_cleanup():
    entry = celery_app.conf.beat_schedule["delete-orphaned-avatars"]

    assert entry["task"] == delete_orphaned_avatars.name
    assert entry["schedule"] == crontab(hour=3, minute=0)
