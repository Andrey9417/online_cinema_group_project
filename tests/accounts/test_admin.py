from unittest.mock import patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from database.models import UserGroupEnum


def group_url(user_id):
    return f"/api/v1/accounts/admin/users/{user_id}/group"


def activate_url(user_id):
    return f"/api/v1/accounts/admin/users/{user_id}/activate"


@pytest.fixture
async def admin(make_user):
    user, _ = await make_user(email="admin@example.com", is_active=True, group=UserGroupEnum.ADMIN)
    return user


# change group

@pytest.mark.parametrize("group", list(UserGroupEnum))
async def test_change_group_success(client, admin, make_user, auth_headers, fetch, user_groups, group):
    target, _ = await make_user(is_active=True)

    response = await client.patch(
        group_url(target.id), json={"group": group.value}, headers=auth_headers(admin)
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": target.id, "email": target.email, "is_active": True, "group": group.value
    }
    assert (await fetch.user(target.email)).group_id == user_groups[group].id


async def test_change_group_applies_on_next_request(client, admin, make_user, auth_headers):
    target, _ = await make_user(is_active=True)
    headers = auth_headers(target)  # token issued before the promotion
    assert (await client.post(activate_url(999_999), headers=headers)).status_code == 403

    await client.patch(group_url(target.id), json={"group": "admin"}, headers=auth_headers(admin))

    assert (await client.post(activate_url(999_999), headers=headers)).status_code == 404


async def test_change_own_group(client, admin, auth_headers, fetch, user_groups):
    response = await client.patch(
        group_url(admin.id), json={"group": "user"}, headers=auth_headers(admin)
    )

    assert response.status_code == 400
    assert (await fetch.user(admin.email)).group_id == user_groups[UserGroupEnum.ADMIN].id


async def test_change_group_unknown_user(client, admin, auth_headers):
    response = await client.patch(
        group_url(999_999), json={"group": "user"}, headers=auth_headers(admin)
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


@pytest.mark.parametrize("body", [{"group": "boss"}, {"group": ""}, {}])
async def test_change_group_invalid_body(client, admin, make_user, auth_headers, body):
    target, _ = await make_user(is_active=True)

    response = await client.patch(group_url(target.id), json=body, headers=auth_headers(admin))

    assert response.status_code == 422


@pytest.mark.parametrize("group", [UserGroupEnum.USER, UserGroupEnum.MODERATOR])
async def test_change_group_non_admin_forbidden(client, make_user, auth_headers, fetch, user_groups, group):
    caller, _ = await make_user(email="caller@example.com", is_active=True, group=group)
    target, _ = await make_user(is_active=True)

    response = await client.patch(
        group_url(target.id), json={"group": "admin"}, headers=auth_headers(caller)
    )

    assert response.status_code == 403
    assert (await fetch.user(target.email)).group_id == user_groups[UserGroupEnum.USER].id


async def test_change_group_requires_auth(client):
    response = await client.patch(group_url(1), json={"group": "admin"})

    assert response.status_code == 401


async def test_change_group_db_error_returns_500(client, admin, make_user, auth_headers, db_session):
    target, _ = await make_user(is_active=True)
    headers = auth_headers(admin)

    with patch.object(db_session, "commit", side_effect=SQLAlchemyError):
        response = await client.patch(group_url(target.id), json={"group": "admin"}, headers=headers)

    assert response.status_code == 500


# manual activation

async def test_admin_activate_success(client, admin, make_user, auth_headers, fetch, login):
    target, _ = await make_user(is_active=False)

    response = await client.post(activate_url(target.id), headers=auth_headers(admin))

    assert response.status_code == 200
    assert response.json() == {"message": "Account activated"}
    assert (await fetch.user(target.email)).is_active is True
    assert await fetch.tokens(target.id) == []
    assert (await login()).status_code == 201


async def test_admin_activate_without_activation_token(client, admin, make_user, auth_headers, fetch):
    target, _ = await make_user(is_active=False, with_token=False)

    response = await client.post(activate_url(target.id), headers=auth_headers(admin))

    assert response.status_code == 200
    assert (await fetch.user(target.email)).is_active is True


async def test_admin_activate_twice(client, admin, make_user, auth_headers):
    target, _ = await make_user(is_active=False)
    await client.post(activate_url(target.id), headers=auth_headers(admin))

    response = await client.post(activate_url(target.id), headers=auth_headers(admin))

    assert response.status_code == 400
    assert response.json()["detail"] == "Account is already active"


async def test_admin_activate_unknown_user(client, admin, auth_headers):
    response = await client.post(activate_url(999_999), headers=auth_headers(admin))

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


@pytest.mark.parametrize("group", [UserGroupEnum.USER, UserGroupEnum.MODERATOR])
async def test_admin_activate_non_admin_forbidden(client, make_user, auth_headers, fetch, group):
    caller, _ = await make_user(email="caller@example.com", is_active=True, group=group)
    target, _ = await make_user(is_active=False)

    response = await client.post(activate_url(target.id), headers=auth_headers(caller))

    assert response.status_code == 403
    assert (await fetch.user(target.email)).is_active is False


async def test_admin_activate_db_error_returns_500(client, admin, make_user, auth_headers, db_session, fetch):
    target, _ = await make_user(is_active=False)
    email, headers = target.email, auth_headers(admin)

    with patch.object(db_session, "commit", side_effect=SQLAlchemyError):
        response = await client.post(activate_url(target.id), headers=headers)

    assert response.status_code == 500
    assert (await fetch.user(email)).is_active is False
