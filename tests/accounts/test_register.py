from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import delete
from sqlalchemy.exc import SQLAlchemyError

from database.models import UserGroup, UserGroupEnum
from security.passwords import verify_password

URL = "/api/v1/accounts/register"
PASSWORD = "Str0ng!Pass"


async def register(client, email="new@example.com", password=PASSWORD):
    return await client.post(URL, json={"email": email, "raw_password": password})


async def test_register_success(client, fetch, user_groups, email_task):
    response = await register(client)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new@example.com"
    assert set(body) == {"id", "email"}  # no password/hash leaks

    user = await fetch.user("new@example.com")
    assert user.id == body["id"]
    assert user.is_active is False
    assert user.group_id == user_groups[UserGroupEnum.USER].id
    assert user.hashed_password != PASSWORD
    assert verify_password(PASSWORD, user.hashed_password)


async def test_register_creates_activation_token_valid_for_24h(client, fetch):
    before = datetime.now(timezone.utc)
    response = await register(client)

    tokens = await fetch.tokens(response.json()["id"])
    assert len(tokens) == 1
    expected = before + timedelta(days=1)
    assert expected - timedelta(minutes=1) <= tokens[0].expires_at <= expected + timedelta(minutes=1)


async def test_register_sends_activation_email(client, fetch, email_task):
    response = await register(client)

    token = (await fetch.tokens(response.json()["id"]))[0]
    email_task.delay.assert_called_once_with("new@example.com", token.token)


async def test_register_lowercases_email(client, fetch):
    response = await register(client, email="New.User@Example.COM")

    assert response.status_code == 201
    assert response.json()["email"] == "new.user@example.com"
    assert await fetch.user("new.user@example.com") is not None


async def test_register_duplicate_email_conflict(client, make_user, email_task):
    await make_user(email="taken@example.com")

    response = await register(client, email="taken@example.com")

    assert response.status_code == 409
    assert "taken@example.com" in response.json()["detail"]
    email_task.delay.assert_not_called()


async def test_register_duplicate_email_different_case_conflict(client, make_user):
    await make_user(email="taken@example.com")

    response = await register(client, email="TAKEN@Example.com")

    assert response.status_code == 409


async def test_register_race_condition_integrity_error_is_conflict(client, make_user, email_task):
    """The pre-check passes, but the unique constraint fires on insert."""
    await make_user(email="taken@example.com")

    with patch("crud.accounts.get_user_by_email", return_value=None):
        response = await register(client, email="taken@example.com")

    assert response.status_code == 409
    email_task.delay.assert_not_called()


async def test_register_weak_password_rejected(client, fetch, email_task):
    response = await register(client, password="weak")

    assert response.status_code == 422
    assert await fetch.user("new@example.com") is None
    email_task.delay.assert_not_called()


async def test_register_invalid_email_rejected(client):
    response = await register(client, email="not-an-email")

    assert response.status_code == 422


async def test_register_missing_fields_rejected(client):
    response = await client.post(URL, json={})

    assert response.status_code == 422


async def test_register_without_user_group_returns_500(client, db_session, email_task):
    await db_session.execute(delete(UserGroup))

    response = await register(client)

    assert response.status_code == 500
    assert response.json()["detail"] == "Such group does not exist"
    email_task.delay.assert_not_called()


async def test_register_db_error_returns_500(client, db_session, email_task):
    with patch.object(db_session, "commit", side_effect=SQLAlchemyError):
        response = await register(client)

    assert response.status_code == 500
    assert response.json()["detail"] == "Something went wrong, try again later"
    email_task.delay.assert_not_called()
