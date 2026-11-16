import re
from io import BytesIO
from unittest.mock import patch

import pytest
from PIL import Image
from sqlalchemy import delete
from sqlalchemy.exc import SQLAlchemyError

from database.models.accounts import UserProfile
from exceptions.storages import S3FileDeleteError, S3FileUploadError
from main import app

URL = "/api/v1/accounts/profile/me/avatar"
OLD_KEY = "avatars/1/old.png"


def image_bytes(fmt: str, size=(10, 10)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, "red").save(buf, format=fmt)
    return buf.getvalue()


async def upload(client, headers, data: bytes, filename="avatar.png", content_type="image/png"):
    return await client.post(
        URL, files={"avatar": (filename, data, content_type)}, headers=headers
    )


@pytest.fixture
async def user(make_user):
    user, _ = await make_user(is_active=True)
    return user


async def set_avatar(db_session, fetch, user_id, key):
    profile = await fetch.profile(user_id)
    profile.avatar = key
    await db_session.commit()


@pytest.mark.parametrize(("fmt", "ext", "mime"), [
    ("PNG", "png", "image/png"),
    ("JPEG", "jpeg", "image/jpeg"),
])
async def test_upload_avatar(client, user, auth_headers, fake_s3, fetch, fmt, ext, mime):
    data = image_bytes(fmt)

    response = await upload(client, auth_headers(user), data)

    assert response.status_code == 200
    key, body, content_type = fake_s3.upload_file.await_args.args
    assert re.fullmatch(rf"avatars/{user.id}/[0-9a-f]{{32}}\.{ext}", key)
    assert body == data  # file pointer was rewound after validation
    assert content_type == mime
    assert (await fetch.profile(user.id)).avatar == key
    assert response.json()["avatar"] == f"http://s3.test/bucket/{key}"


async def test_format_is_detected_from_content_not_filename(client, user, auth_headers, fake_s3):
    await upload(client, auth_headers(user), image_bytes("JPEG"), filename="pic.png")

    key, _, content_type = fake_s3.upload_file.await_args.args
    assert key.endswith(".jpeg")
    assert content_type == "image/jpeg"


async def test_each_upload_gets_new_key(client, user, auth_headers, fake_s3):
    headers = auth_headers(user)
    await upload(client, headers, image_bytes("PNG"))
    await upload(client, headers, image_bytes("PNG"))

    first, second = (call.args[0] for call in fake_s3.upload_file.await_args_list)
    assert first != second


async def test_first_upload_does_not_delete_anything(client, user, auth_headers, fake_s3):
    await upload(client, auth_headers(user), image_bytes("PNG"))

    fake_s3.delete_file.assert_not_called()


async def test_old_avatar_deleted_after_replace(client, user, auth_headers, fake_s3, fetch, db_session):
    await set_avatar(db_session, fetch, user.id, OLD_KEY)

    response = await upload(client, auth_headers(user), image_bytes("PNG"))

    assert response.status_code == 200
    fake_s3.delete_file.assert_awaited_once_with(OLD_KEY)
    assert (await fetch.profile(user.id)).avatar != OLD_KEY


async def test_old_avatar_delete_failure_still_succeeds(client, user, auth_headers, fake_s3, fetch, db_session):
    await set_avatar(db_session, fetch, user.id, OLD_KEY)
    fake_s3.delete_file.side_effect = S3FileDeleteError("boom")

    response = await upload(client, auth_headers(user), image_bytes("PNG"))

    assert response.status_code == 200
    assert (await fetch.profile(user.id)).avatar == fake_s3.upload_file.await_args.args[0]


async def test_s3_upload_error(client, user, auth_headers, fake_s3, fetch, db_session):
    await set_avatar(db_session, fetch, user.id, OLD_KEY)
    fake_s3.upload_file.side_effect = S3FileUploadError("boom")

    response = await upload(client, auth_headers(user), image_bytes("PNG"))

    assert response.status_code == 503
    assert response.json()["detail"] == "Avatar not uploaded, try again later"
    assert (await fetch.profile(user.id)).avatar == OLD_KEY
    fake_s3.delete_file.assert_not_called()


async def test_db_error_returns_500_and_deletes_uploaded_file(client, user, auth_headers, fake_s3, db_session):
    headers = auth_headers(user)

    with patch.object(db_session, "commit", side_effect=SQLAlchemyError):
        response = await upload(client, headers, image_bytes("PNG"))

    assert response.status_code == 500
    uploaded_key = fake_s3.upload_file.await_args.args[0]
    fake_s3.delete_file.assert_awaited_once_with(uploaded_key)


async def test_db_error_keeps_old_avatar(client, user, auth_headers, fake_s3, fetch, db_session):
    user_id = user.id  # the failed commit's rollback expires `user`; reading it later would lazy-load
    await set_avatar(db_session, fetch, user_id, OLD_KEY)
    headers = auth_headers(user)

    with patch.object(db_session, "commit", side_effect=SQLAlchemyError):
        response = await upload(client, headers, image_bytes("PNG"))

    assert response.status_code == 500
    # only the new upload is cleaned up; the still-referenced old avatar stays
    fake_s3.delete_file.assert_awaited_once_with(fake_s3.upload_file.await_args.args[0])
    assert (await fetch.profile(user_id)).avatar == OLD_KEY


async def test_db_error_cleanup_failure_still_returns_500(client, user, auth_headers, fake_s3, db_session):
    fake_s3.delete_file.side_effect = S3FileDeleteError("boom")
    headers = auth_headers(user)

    with patch.object(db_session, "commit", side_effect=SQLAlchemyError):
        response = await upload(client, headers, image_bytes("PNG"))

    assert response.status_code == 500
    fake_s3.delete_file.assert_awaited_once()


async def test_missing_profile_returns_404_and_deletes_uploaded_file(client, user, auth_headers, fake_s3, db_session):
    await db_session.execute(delete(UserProfile).where(UserProfile.user_id == user.id))
    await db_session.commit()

    response = await upload(client, auth_headers(user), image_bytes("PNG"))

    assert response.status_code == 404
    assert response.json()["detail"] == "Profile not found"
    fake_s3.delete_file.assert_awaited_once_with(fake_s3.upload_file.await_args.args[0])


async def test_missing_profile_cleanup_failure_still_returns_404(client, user, auth_headers, fake_s3, db_session):
    await db_session.execute(delete(UserProfile).where(UserProfile.user_id == user.id))
    await db_session.commit()
    fake_s3.delete_file.side_effect = S3FileDeleteError("boom")

    response = await upload(client, auth_headers(user), image_bytes("PNG"))

    assert response.status_code == 404


async def test_fake_image_rejected(client, user, auth_headers, fake_s3):
    response = await upload(client, auth_headers(user), b"definitely not a png")

    assert response.status_code == 422
    assert "Invalid image format" in response.text
    fake_s3.upload_file.assert_not_called()


async def test_gif_rejected(client, user, auth_headers, fake_s3):
    response = await upload(
        client, auth_headers(user), image_bytes("GIF"), filename="a.gif", content_type="image/gif"
    )

    assert response.status_code == 422
    assert "Unsupported image format: GIF" in response.text
    fake_s3.upload_file.assert_not_called()


async def test_too_large_rejected(client, user, auth_headers, fake_s3):
    response = await upload(client, auth_headers(user), b"\0" * (2 * 1024 * 1024 + 1))

    assert response.status_code == 422
    assert "Image size exceeds 2 MB" in response.text
    fake_s3.upload_file.assert_not_called()


async def test_exactly_2mb_is_not_rejected_for_size(client, user, auth_headers, fake_s3):
    response = await upload(client, auth_headers(user), b"\0" * (2 * 1024 * 1024))

    assert "exceeds 2 MB" not in response.text


async def test_missing_file(client, user, auth_headers, fake_s3):
    response = await client.post(URL, headers=auth_headers(user))

    assert response.status_code == 422


async def test_requires_auth(client, fake_s3):
    response = await upload(client, {}, image_bytes("PNG"))

    assert response.status_code == 401
    fake_s3.upload_file.assert_not_called()


def test_openapi_advertises_multipart():
    """Regression: a Form() model made Swagger send multipart with a urlencoded header."""
    content = app.openapi()["paths"][URL]["post"]["requestBody"]["content"]

    assert list(content) == ["multipart/form-data"]
