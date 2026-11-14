from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy.exc import SQLAlchemyError

URL = "/api/v1/accounts/activate"


async def activate(client, token):
    return await client.get(URL, params={"token": token})


async def test_activate_success(client, make_user, fetch):
    user, token = await make_user()

    response = await activate(client, token.token)

    assert response.status_code == 200
    assert response.json() == {"message": "Account activation is a success"}
    assert (await fetch.user(user.email)).is_active is True
    assert await fetch.tokens(user.id) == []


async def test_activate_token_cannot_be_reused(client, make_user):
    _, token = await make_user()
    await activate(client, token.token)

    response = await activate(client, token.token)

    assert response.status_code == 400
    assert response.json()["detail"] == "Wrong token"


async def test_activate_unknown_token(client, make_user, fetch):
    user, _ = await make_user()

    response = await activate(client, "definitely-not-a-real-token")

    assert response.status_code == 400
    assert response.json()["detail"] == "Wrong token"
    assert (await fetch.user(user.email)).is_active is False


async def test_activate_missing_token_param(client):
    response = await client.get(URL)

    assert response.status_code == 422


async def test_activate_expired_token(client, make_user, fetch):
    user, token = await make_user(
        token_expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)
    )

    response = await activate(client, token.token)

    assert response.status_code == 400
    assert response.json()["detail"] == "Token expired"
    assert (await fetch.user(user.email)).is_active is False


async def test_activate_already_active_account_removes_leftover_token(client, make_user, fetch):
    user, token = await make_user(is_active=True)

    response = await activate(client, token.token)

    assert response.status_code == 400
    assert response.json()["detail"] == "Account is already active"
    assert await fetch.tokens(user.id) == []


async def test_activate_db_error_returns_500(client, db_session, make_user, fetch):
    user, token = await make_user()
    email, user_id = user.email, user.id  # rollback expires ORM objects

    with patch.object(db_session, "commit", side_effect=SQLAlchemyError):
        response = await activate(client, token.token)

    assert response.status_code == 500
    assert response.json()["detail"] == "Something went wrong, try again later"
    assert (await fetch.user(email)).is_active is False
    assert len(await fetch.tokens(user_id)) == 1
