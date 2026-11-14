from datetime import timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from config.dependencies import require_group
from database.models import UserGroupEnum
from security.tokens import JWTTokenTypes, create_access_token, create_refresh_token, generate_jwt_token

# any CurrentUser endpoint works; this one has no side effects
URL = "/api/v1/accounts/profile/me"


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


# get_current_user

async def test_active_user_passes(client, make_user, auth_headers):
    user, _ = await make_user(is_active=True)

    response = await client.get(URL, headers=auth_headers(user))

    assert response.status_code == 200


async def test_no_auth_header(client):
    response = await client.get(URL)

    assert response.status_code == 401


async def test_garbage_token(client):
    response = await client.get(URL, headers=bearer("garbage"))

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


async def test_refresh_token_instead_of_access(client, make_user):
    user, _ = await make_user(is_active=True)

    response = await client.get(URL, headers=bearer(create_refresh_token(user.id)))

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


async def test_expired_access_token(client, make_user):
    user, _ = await make_user(is_active=True)
    token = generate_jwt_token(user.id, JWTTokenTypes.ACCESS, timedelta(seconds=-1))

    response = await client.get(URL, headers=bearer(token))

    assert response.status_code == 401


async def test_token_for_deleted_user(client):
    response = await client.get(URL, headers=bearer(create_access_token(999_999)))

    assert response.status_code == 401
    assert response.json()["detail"] == "User not found"


async def test_inactive_user(client, make_user, auth_headers):
    user, _ = await make_user(is_active=False)

    response = await client.get(URL, headers=auth_headers(user))

    assert response.status_code == 403
    assert response.json()["detail"] == "Account is not active"


# require_group

ORDER = [UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN]


@pytest.mark.parametrize("user_group", ORDER)
@pytest.mark.parametrize("required_group", ORDER)
async def test_require_group(user_group, required_group):
    checker = require_group(required_group)
    user = SimpleNamespace(group=SimpleNamespace(name=user_group))

    if ORDER.index(user_group) >= ORDER.index(required_group):
        assert await checker(user) is user
    else:
        with pytest.raises(HTTPException) as exc:
            await checker(user)
        assert exc.value.status_code == 403
        assert exc.value.detail == "You have no rights here!"
