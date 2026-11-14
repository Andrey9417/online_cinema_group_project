from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy.exc import SQLAlchemyError

from config.settings import settings
from security.tokens import JWTTokenTypes, decode_jwt_token


async def test_login_success_returns_token_pair(login, make_user):
    user, _ = await make_user(is_active=True)

    response = await login()

    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert decode_jwt_token(body["access_token"], JWTTokenTypes.ACCESS)["user_id"] == str(user.id)
    assert decode_jwt_token(body["refresh_token"], JWTTokenTypes.REFRESH)["user_id"] == str(user.id)


async def test_login_stores_refresh_token(login, make_user, fetch):
    user, _ = await make_user(is_active=True)
    before = datetime.now(timezone.utc)

    response = await login()

    rows = await fetch.refresh_tokens(user.id)
    assert [row.token for row in rows] == [response.json()["refresh_token"]]
    expected = before + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    assert expected - timedelta(minutes=1) <= rows[0].expires_at <= expected + timedelta(minutes=1)


async def test_each_login_creates_separate_session(login, make_user, fetch):
    user, _ = await make_user(is_active=True)

    first = await login()
    second = await login()

    assert first.json()["refresh_token"] != second.json()["refresh_token"]
    assert len(await fetch.refresh_tokens(user.id)) == 2


async def test_login_email_is_case_insensitive(login, make_user):
    await make_user(is_active=True)

    response = await login(email="User@Example.COM")

    assert response.status_code == 201


async def test_login_wrong_password(login, make_user, fetch):
    user, _ = await make_user(is_active=True)

    response = await login(password="Wr0ng!Pass")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"
    assert await fetch.refresh_tokens(user.id) == []


async def test_login_unknown_email_same_error_as_wrong_password(login):
    response = await login(email="nobody@example.com")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


async def test_login_inactive_account(login, make_user, fetch):
    user, _ = await make_user(is_active=False)

    response = await login()

    assert response.status_code == 403
    assert response.json()["detail"] == "Account is not active"
    assert await fetch.refresh_tokens(user.id) == []


async def test_login_inactive_account_with_wrong_password_does_not_reveal_status(login, make_user):
    await make_user(is_active=False)

    response = await login(password="Wr0ng!Pass")

    assert response.status_code == 401


async def test_login_missing_fields(client):
    response = await client.post("/api/v1/accounts/login", json={"email": "user@example.com"})

    assert response.status_code == 422


async def test_login_db_error_returns_500(login, make_user, db_session, fetch):
    user, _ = await make_user(is_active=True)
    user_id = user.id

    with patch.object(db_session, "commit", side_effect=SQLAlchemyError):
        response = await login()

    assert response.status_code == 500
    assert response.json()["detail"] == "Something went wrong, try again later"
    assert await fetch.refresh_tokens(user_id) == []
