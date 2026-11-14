from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy.exc import SQLAlchemyError

from config.settings import settings
from database.models.accounts import PasswordResetToken
from security.passwords import verify_password

STRONG_PASSWORD = "Str0ng!Pass"  # make_user's password

CHANGE_URL = "/api/v1/accounts/password/change"
RESET_REQUEST_URL = "/api/v1/accounts/password/reset/request"
RESET_COMPLETE_URL = "/api/v1/accounts/password/reset/complete"
NEW_PASSWORD = "N3w!Passw0rd"


async def change(client, headers, old=STRONG_PASSWORD, new=NEW_PASSWORD):
    return await client.post(
        CHANGE_URL, json={"old_password": old, "new_password": new}, headers=headers
    )


async def request_reset(client, email="user@example.com"):
    return await client.post(RESET_REQUEST_URL, json={"email": email})


async def complete_reset(client, token, new=NEW_PASSWORD):
    return await client.post(RESET_COMPLETE_URL, json={"token": token, "new_password": new})


async def make_reset_token(db_session, user, expires_at=None):
    token = PasswordResetToken(user_id=user.id)
    if expires_at is not None:
        token.expires_at = expires_at
    db_session.add(token)
    await db_session.commit()
    return token


# change

async def test_change_password_success(client, make_user, auth_headers, fetch):
    user, _ = await make_user(is_active=True)

    response = await change(client, auth_headers(user))

    assert response.status_code == 200
    assert response.json() == {"message": "Password changed, log in again"}
    hashed = (await fetch.user(user.email)).hashed_password
    assert verify_password(NEW_PASSWORD, hashed)
    assert not verify_password(STRONG_PASSWORD, hashed)


async def test_change_password_logs_out_everywhere(client, make_user, login, auth_headers, fetch):
    user, _ = await make_user(is_active=True)
    tokens = (await login()).json()
    await login()

    await change(client, auth_headers(user))

    assert await fetch.refresh_tokens(user.id) == []
    refresh = await client.post(
        "/api/v1/accounts/refresh-token", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh.status_code == 401


async def test_change_password_then_login_with_new_one(client, make_user, login, auth_headers):
    user, _ = await make_user(is_active=True)
    await change(client, auth_headers(user))

    assert (await login(password=STRONG_PASSWORD)).status_code == 401
    assert (await login(password=NEW_PASSWORD)).status_code == 201


async def test_change_password_wrong_old(client, make_user, login, auth_headers, fetch):
    user, _ = await make_user(is_active=True)
    await login()

    response = await change(client, auth_headers(user), old="Wr0ng!Pass")

    assert response.status_code == 400
    assert response.json()["detail"] == "Old password is incorrect"
    assert verify_password(STRONG_PASSWORD, (await fetch.user(user.email)).hashed_password)
    assert len(await fetch.refresh_tokens(user.id)) == 1


async def test_change_password_weak_new(client, make_user, auth_headers, fetch):
    user, _ = await make_user(is_active=True)

    response = await change(client, auth_headers(user), new="weak")

    assert response.status_code == 422
    assert verify_password(STRONG_PASSWORD, (await fetch.user(user.email)).hashed_password)


async def test_change_password_requires_auth(client):
    response = await change(client, headers={})

    assert response.status_code == 401


async def test_change_password_db_error_returns_500(client, make_user, auth_headers, db_session):
    user, _ = await make_user(is_active=True)

    with patch.object(db_session, "commit", side_effect=SQLAlchemyError):
        response = await change(client, auth_headers(user))

    assert response.status_code == 500


# reset request

async def test_reset_request_creates_token_and_sends_email(client, make_user, fetch, reset_email_task):
    user, _ = await make_user(is_active=True)
    before = datetime.now(timezone.utc)

    response = await request_reset(client)

    assert response.status_code == 200
    assert response.json() == {"message": "Reset token has been sent"}
    tokens = await fetch.reset_tokens(user.id)
    assert len(tokens) == 1
    expected = before + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    assert expected - timedelta(minutes=1) <= tokens[0].expires_at <= expected + timedelta(minutes=1)
    reset_email_task.delay.assert_called_once_with(user.email, tokens[0].token)


async def test_reset_request_email_is_case_insensitive(client, make_user, reset_email_task):
    await make_user(is_active=True)

    await request_reset(client, email="USER@example.com")

    reset_email_task.delay.assert_called_once()


async def test_reset_request_replaces_old_token(client, make_user, fetch, db_session):
    user, _ = await make_user(is_active=True)
    user_id = user.id
    await request_reset(client)
    old = (await fetch.reset_tokens(user_id))[0].token
    # Real requests get a fresh session; here the cached User still has
    # password_reset_token=None from the first request, so drop the cache.
    db_session.expire_all()

    response = await request_reset(client)

    assert response.status_code == 200
    tokens = await fetch.reset_tokens(user_id)
    assert len(tokens) == 1
    assert tokens[0].token != old


async def test_reset_request_unknown_email_same_response(client, reset_email_task):
    response = await request_reset(client, email="nobody@example.com")

    assert response.status_code == 200
    assert response.json() == {"message": "Reset token has been sent"}
    reset_email_task.delay.assert_not_called()


async def test_reset_request_inactive_user_same_response(client, make_user, fetch, reset_email_task):
    user, _ = await make_user(is_active=False)

    response = await request_reset(client)

    assert response.status_code == 200
    assert response.json() == {"message": "Reset token has been sent"}
    assert await fetch.reset_tokens(user.id) == []
    reset_email_task.delay.assert_not_called()


async def test_reset_request_invalid_email(client):
    response = await request_reset(client, email="not-an-email")

    assert response.status_code == 422


async def test_reset_request_db_error_returns_500(client, make_user, db_session, reset_email_task):
    await make_user(is_active=True)

    with patch.object(db_session, "commit", side_effect=SQLAlchemyError):
        response = await request_reset(client)

    assert response.status_code == 500
    reset_email_task.delay.assert_not_called()


# reset complete

async def test_reset_complete_success(client, make_user, db_session, login, fetch):
    user, _ = await make_user(is_active=True)
    await login()
    token = await make_reset_token(db_session, user)

    response = await complete_reset(client, token.token)

    assert response.status_code == 200
    assert response.json() == {"message": "Password has been reset, log in"}
    assert verify_password(NEW_PASSWORD, (await fetch.user(user.email)).hashed_password)
    assert await fetch.reset_tokens(user.id) == []
    assert await fetch.refresh_tokens(user.id) == []
    assert (await login(password=NEW_PASSWORD)).status_code == 201


async def test_reset_full_flow(client, make_user, reset_email_task, login):
    await make_user(is_active=True)
    await request_reset(client)
    token = reset_email_task.delay.call_args.args[1]

    response = await complete_reset(client, token)

    assert response.status_code == 200
    assert (await login(password=NEW_PASSWORD)).status_code == 201


async def test_reset_complete_token_cannot_be_reused(client, make_user, db_session):
    user, _ = await make_user(is_active=True)
    token = await make_reset_token(db_session, user)
    await complete_reset(client, token.token)

    response = await complete_reset(client, token.token, new="An0ther!Pass")

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid token"


async def test_reset_complete_unknown_token(client):
    response = await complete_reset(client, "never-issued")

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid token"


async def test_reset_complete_expired_token_is_deleted(client, make_user, db_session, fetch):
    user, _ = await make_user(is_active=True)
    token = await make_reset_token(
        db_session, user, expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)
    )

    response = await complete_reset(client, token.token)

    assert response.status_code == 400
    assert response.json()["detail"] == "Token expired"
    assert await fetch.reset_tokens(user.id) == []
    assert verify_password(STRONG_PASSWORD, (await fetch.user(user.email)).hashed_password)


async def test_reset_complete_weak_password_keeps_token(client, make_user, db_session, fetch):
    user, _ = await make_user(is_active=True)
    token = await make_reset_token(db_session, user)

    response = await complete_reset(client, token.token, new="weak")

    assert response.status_code == 422
    assert len(await fetch.reset_tokens(user.id)) == 1


async def test_reset_complete_db_error_returns_500(client, make_user, db_session, fetch):
    user, _ = await make_user(is_active=True)
    token = await make_reset_token(db_session, user)
    user_id, value = user.id, token.token

    with patch.object(db_session, "commit", side_effect=SQLAlchemyError):
        response = await complete_reset(client, value)

    assert response.status_code == 500
    assert len(await fetch.reset_tokens(user_id)) == 1
