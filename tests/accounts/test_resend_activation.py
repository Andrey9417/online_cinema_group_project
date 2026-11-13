from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy.exc import SQLAlchemyError

URL = "/api/v1/resend-activation"
MESSAGE = {"message": "Check your email for the new activation link"}


async def resend(client, email="user@example.com"):
    return await client.post(URL, json={"email": email})


def expired():
    return datetime.now(timezone.utc) - timedelta(hours=1)


async def test_resend_replaces_expired_token(client, make_user, fetch, email_task):
    user, old_token = await make_user(token_expires_at=expired())
    old_value = old_token.token

    response = await resend(client)

    assert response.status_code == 200
    assert response.json() == MESSAGE
    tokens = await fetch.tokens(user.id)
    assert len(tokens) == 1
    assert tokens[0].token != old_value
    assert tokens[0].expires_at > datetime.now(timezone.utc) + timedelta(hours=23)
    email_task.delay.assert_called_once_with(user.email, tokens[0].token)


async def test_resend_replaces_still_valid_token(client, make_user, fetch, email_task):
    user, old_token = await make_user()
    old_value = old_token.token

    response = await resend(client)

    assert response.status_code == 200
    tokens = await fetch.tokens(user.id)
    assert len(tokens) == 1
    assert tokens[0].token != old_value
    email_task.delay.assert_called_once_with(user.email, tokens[0].token)


async def test_resend_for_inactive_user_without_token(client, make_user, fetch, email_task):
    """E.g. the old token was already removed by the celery-beat cleanup."""
    user, _ = await make_user(with_token=False)

    response = await resend(client)

    assert response.status_code == 200
    tokens = await fetch.tokens(user.id)
    assert len(tokens) == 1
    email_task.delay.assert_called_once_with(user.email, tokens[0].token)


async def test_resent_token_activates_and_old_one_does_not(client, make_user, fetch):
    user, old_token = await make_user(token_expires_at=expired())
    old_value = old_token.token
    await resend(client)
    new_value = (await fetch.tokens(user.id))[0].token

    old_response = await client.get("/api/v1/activate", params={"token": old_value})
    new_response = await client.get("/api/v1/activate", params={"token": new_value})

    assert old_response.status_code == 400
    assert new_response.status_code == 200
    assert (await fetch.user(user.email)).is_active is True


async def test_resend_unknown_email_gives_same_response(client, email_task):
    response = await resend(client, email="ghost@example.com")

    assert response.status_code == 200
    assert response.json() == MESSAGE
    email_task.delay.assert_not_called()


async def test_resend_active_user_gives_same_response(client, make_user, fetch, email_task):
    user, _ = await make_user(is_active=True)

    response = await resend(client)

    assert response.status_code == 200
    assert response.json() == MESSAGE
    assert await fetch.tokens(user.id) == []
    email_task.delay.assert_not_called()


async def test_resend_active_user_without_token_gives_same_response(client, make_user, email_task):
    await make_user(is_active=True, with_token=False)

    response = await resend(client)

    assert response.status_code == 200
    assert response.json() == MESSAGE
    email_task.delay.assert_not_called()


async def test_resend_invalid_email_rejected(client):
    response = await resend(client, email="not-an-email")

    assert response.status_code == 422


async def test_resend_email_is_case_insensitive(client, make_user, email_task):
    await make_user(email="user@example.com")

    await resend(client, email="User@Example.com")

    email_task.delay.assert_called_once()


async def test_resend_db_error_returns_500(client, db_session, make_user, fetch, email_task):
    user, _ = await make_user(with_token=False)
    user_id = user.id  # rollback expires ORM objects

    with patch.object(db_session, "commit", side_effect=SQLAlchemyError):
        response = await resend(client)

    assert response.status_code == 500
    assert response.json()["detail"] == "Something went wrong, try again later"
    assert await fetch.tokens(user_id) == []
    email_task.delay.assert_not_called()
