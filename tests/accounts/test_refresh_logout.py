from datetime import timedelta
from unittest.mock import patch

from sqlalchemy.exc import SQLAlchemyError

from security.tokens import (
    JWTTokenTypes,
    create_refresh_token,
    decode_jwt_token,
    generate_jwt_token,
)

REFRESH_URL = "/api/v1/accounts/refresh-token"
LOGOUT_URL = "/api/v1/accounts/logout"


async def refresh(client, token):
    return await client.post(REFRESH_URL, json={"refresh_token": token})


async def logout(client, token):
    return await client.post(LOGOUT_URL, json={"refresh_token": token})


async def logged_in(make_user, login):
    user, _ = await make_user(is_active=True)
    return user, (await login()).json()


# refresh

async def test_refresh_returns_new_access_token(client, make_user, login):
    user, tokens = await logged_in(make_user, login)

    response = await refresh(client, tokens["refresh_token"])

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] != tokens["access_token"]
    assert decode_jwt_token(body["access_token"], JWTTokenTypes.ACCESS)["user_id"] == str(user.id)


async def test_refresh_new_access_token_works(client, make_user, login):
    _, tokens = await logged_in(make_user, login)
    access = (await refresh(client, tokens["refresh_token"])).json()["access_token"]

    response = await client.get(
        "/api/v1/accounts/profile/me", headers={"Authorization": f"Bearer {access}"}
    )

    assert response.status_code == 200


async def test_refresh_garbage_token(client):
    response = await refresh(client, "garbage")

    assert response.status_code == 401


async def test_refresh_with_access_token(client, make_user, login):
    _, tokens = await logged_in(make_user, login)

    response = await refresh(client, tokens["access_token"])

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token type"


async def test_refresh_expired_token(client):
    token = generate_jwt_token(1, JWTTokenTypes.REFRESH, timedelta(seconds=-1))

    response = await refresh(client, token)

    assert response.status_code == 401
    assert response.json()["detail"] == "Token expired"


async def test_refresh_valid_jwt_not_in_db(client, make_user):
    user, _ = await make_user(is_active=True)

    response = await refresh(client, create_refresh_token(user.id))

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


async def test_refresh_after_logout(client, make_user, login):
    _, tokens = await logged_in(make_user, login)
    await logout(client, tokens["refresh_token"])

    response = await refresh(client, tokens["refresh_token"])

    assert response.status_code == 401


async def test_refresh_missing_field(client):
    response = await client.post(REFRESH_URL, json={})

    assert response.status_code == 422


# logout

async def test_logout_deletes_refresh_token(client, make_user, login, fetch):
    user, tokens = await logged_in(make_user, login)

    response = await logout(client, tokens["refresh_token"])

    assert response.status_code == 200
    assert response.json() == {"message": "Come back =("}
    assert await fetch.refresh_tokens(user.id) == []


async def test_logout_keeps_other_sessions(client, make_user, login, fetch):
    user, tokens = await logged_in(make_user, login)
    other = (await login()).json()

    await logout(client, tokens["refresh_token"])

    assert [row.token for row in await fetch.refresh_tokens(user.id)] == [other["refresh_token"]]


async def test_logout_twice_is_ok(client, make_user, login):
    _, tokens = await logged_in(make_user, login)
    await logout(client, tokens["refresh_token"])

    response = await logout(client, tokens["refresh_token"])

    assert response.status_code == 200


async def test_logout_unknown_token_is_ok(client):
    response = await logout(client, "never-issued")

    assert response.status_code == 200


async def test_logout_db_error_returns_500(client, make_user, login, db_session, fetch):
    user, tokens = await logged_in(make_user, login)
    user_id = user.id

    with patch.object(db_session, "commit", side_effect=SQLAlchemyError):
        response = await logout(client, tokens["refresh_token"])

    assert response.status_code == 500
    assert len(await fetch.refresh_tokens(user_id)) == 1
