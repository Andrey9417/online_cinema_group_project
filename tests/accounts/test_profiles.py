from datetime import date, timedelta
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from sqlalchemy import delete
from sqlalchemy.exc import SQLAlchemyError

from database.models.accounts import UserProfile
from schemas.accounts import UserProfileUpdateSchema

URL = "/api/v1/accounts/profile/me"
EMPTY_PROFILE = {
    "first_name": None,
    "last_name": None,
    "gender": None,
    "date_of_birth": None,
    "info": None,
    "avatar": None,
}


@pytest.fixture
async def user(make_user):
    user, _ = await make_user(is_active=True)
    return user


async def test_register_creates_empty_profile(client, fetch):
    response = await client.post(
        "/api/v1/accounts/register", json={"email": "new@example.com", "raw_password": "Str0ng!Pass"}
    )

    profile = await fetch.profile(response.json()["id"])
    assert profile is not None
    assert profile.first_name is None and profile.avatar is None


# GET

async def test_get_profile(client, user, auth_headers, fake_s3):
    response = await client.get(URL, headers=auth_headers(user))

    assert response.status_code == 200
    assert response.json() == EMPTY_PROFILE
    fake_s3.get_file_url.assert_not_called()


async def test_get_profile_returns_avatar_url_not_key(client, user, auth_headers, fake_s3, fetch, db_session):
    profile = await fetch.profile(user.id)
    profile.avatar = "avatars/1/abc.png"
    await db_session.commit()

    response = await client.get(URL, headers=auth_headers(user))

    assert response.json()["avatar"] == "http://s3.test/bucket/avatars/1/abc.png"
    fake_s3.get_file_url.assert_awaited_once_with("avatars/1/abc.png")


async def test_get_profile_missing(client, user, auth_headers, db_session):
    await db_session.execute(delete(UserProfile).where(UserProfile.user_id == user.id))
    await db_session.commit()

    response = await client.get(URL, headers=auth_headers(user))

    assert response.status_code == 404
    assert response.json()["detail"] == "Profile not found"


async def test_get_profile_requires_auth(client):
    assert (await client.get(URL)).status_code == 401


# PATCH

async def test_update_profile(client, user, auth_headers, fetch):
    data = {
        "first_name": "John",
        "last_name": "Doe",
        "gender": "man",
        "date_of_birth": "1990-05-17",
        "info": "Likes movies",
    }

    response = await client.patch(URL, json=data, headers=auth_headers(user))

    assert response.status_code == 200
    assert response.json() == {**data, "avatar": None}
    profile = await fetch.profile(user.id)
    assert profile.first_name == "John"
    assert profile.date_of_birth == date(1990, 5, 17)


async def test_partial_update_keeps_other_fields(client, user, auth_headers):
    headers = auth_headers(user)
    await client.patch(URL, json={"first_name": "John", "info": "Hi"}, headers=headers)

    response = await client.patch(URL, json={"last_name": "Doe"}, headers=headers)

    body = response.json()
    assert (body["first_name"], body["last_name"], body["info"]) == ("John", "Doe", "Hi")


async def test_explicit_null_clears_field(client, user, auth_headers):
    headers = auth_headers(user)
    await client.patch(URL, json={"first_name": "John", "last_name": "Doe"}, headers=headers)

    response = await client.patch(URL, json={"first_name": None}, headers=headers)

    assert response.json()["first_name"] is None
    assert response.json()["last_name"] == "Doe"


async def test_empty_update_changes_nothing(client, user, auth_headers):
    response = await client.patch(URL, json={}, headers=auth_headers(user))

    assert response.status_code == 200
    assert response.json() == EMPTY_PROFILE


async def test_update_strips_whitespace(client, user, auth_headers):
    response = await client.patch(
        URL, json={"first_name": "  John ", "last_name": " Doe  ", "info": "  bio  "},
        headers=auth_headers(user),
    )

    body = response.json()
    assert (body["first_name"], body["last_name"], body["info"]) == ("John", "Doe", "bio")


async def test_update_cannot_set_avatar(client, user, auth_headers, fetch):
    await client.patch(URL, json={"avatar": "avatars/evil.png"}, headers=auth_headers(user))

    assert (await fetch.profile(user.id)).avatar is None


@pytest.mark.parametrize("data", [
    {"first_name": "a" * 101},
    {"last_name": "a" * 101},
    {"info": "a" * 1001},
    {"gender": "other"},
    {"date_of_birth": (date.today() + timedelta(days=1)).isoformat()},
    {"date_of_birth": "1899-12-31"},
    {"date_of_birth": "not-a-date"},
])
async def test_update_validation(client, user, auth_headers, fetch, data):
    response = await client.patch(URL, json=data, headers=auth_headers(user))

    assert response.status_code == 422
    profile = await fetch.profile(user.id)
    assert (profile.first_name, profile.gender, profile.date_of_birth) == (None, None, None)


async def test_update_profile_missing(client, user, auth_headers, db_session):
    await db_session.execute(delete(UserProfile).where(UserProfile.user_id == user.id))
    await db_session.commit()

    response = await client.patch(URL, json={"first_name": "John"}, headers=auth_headers(user))

    assert response.status_code == 404


async def test_update_requires_auth(client):
    assert (await client.patch(URL, json={"first_name": "John"})).status_code == 401


async def test_update_db_error_returns_500(client, user, auth_headers, db_session):
    headers = auth_headers(user)

    with patch.object(db_session, "commit", side_effect=SQLAlchemyError):
        response = await client.patch(URL, json={"first_name": "John"}, headers=headers)

    assert response.status_code == 500


# schema boundaries

@pytest.mark.parametrize("value", [date(1900, 1, 1), date.today()])
def test_birth_date_boundaries_accepted(value):
    assert UserProfileUpdateSchema(date_of_birth=value).date_of_birth == value


def test_max_length_boundaries_accepted():
    schema = UserProfileUpdateSchema(first_name="a" * 100, last_name="a" * 100, info="a" * 1000)

    assert len(schema.first_name) == 100 and len(schema.info) == 1000


def test_unset_fields_are_excluded():
    assert UserProfileUpdateSchema(first_name="John").model_dump(exclude_unset=True) == {
        "first_name": "John"
    }


def test_gender_enum_values():
    assert UserProfileUpdateSchema(gender="woman").gender == "woman"
    with pytest.raises(ValidationError):
        UserProfileUpdateSchema(gender="WOMAN")
