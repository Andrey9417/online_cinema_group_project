from unittest.mock import AsyncMock, MagicMock

import pytest
from botocore.exceptions import BotoCoreError, ClientError

from config.dependencies import get_s3_storage_client
from config.settings import settings
from exceptions.storages import S3FileDeleteError, S3FileUploadError
from storages import S3StorageClient


@pytest.fixture
def storage():
    return S3StorageClient(
        endpoint_url="http://minio:9000",
        public_url="http://localhost:9000/",
        access_key="key",
        secret_key="secret",
        bucket_name="bucket",
    )


@pytest.fixture
def s3(storage):
    """Stands in for the object yielded by `async with session.client("s3", ...)`."""
    s3 = AsyncMock()
    storage._session = MagicMock()
    storage._session.client.return_value.__aenter__.return_value = s3
    return s3


def client_error(op):
    return ClientError({"Error": {"Code": "500", "Message": "boom"}}, op)


async def test_get_file_url(storage):
    assert await storage.get_file_url("avatars/1/a.png") == "http://localhost:9000/bucket/avatars/1/a.png"


async def test_get_file_url_quotes_key(storage):
    assert await storage.get_file_url("avatars/1/my pic.png") == (
        "http://localhost:9000/bucket/avatars/1/my%20pic.png"
    )


async def test_upload_file(storage, s3):
    await storage.upload_file("avatars/1/a.png", b"data", "image/png")

    s3.put_object.assert_awaited_once_with(
        Bucket="bucket", Key="avatars/1/a.png", Body=b"data", ContentType="image/png"
    )


async def test_client_uses_endpoint_and_path_addressing(storage, s3):
    await storage.upload_file("a.png", b"data", "image/png")

    args, kwargs = storage._session.client.call_args
    assert args == ("s3",)
    assert kwargs["endpoint_url"] == "http://minio:9000"
    assert kwargs["config"].s3 == {"addressing_style": "path"}


@pytest.mark.parametrize("error", [client_error("PutObject"), BotoCoreError()])
async def test_upload_file_error(storage, s3, error):
    s3.put_object.side_effect = error

    with pytest.raises(S3FileUploadError):
        await storage.upload_file("a.png", b"data", "image/png")


async def test_delete_file(storage, s3):
    await storage.delete_file("avatars/1/a.png")

    s3.delete_object.assert_awaited_once_with(Bucket="bucket", Key="avatars/1/a.png")


@pytest.mark.parametrize("error", [client_error("DeleteObject"), BotoCoreError()])
async def test_delete_file_error(storage, s3, error):
    s3.delete_object.side_effect = error

    with pytest.raises(S3FileDeleteError):
        await storage.delete_file("a.png")


async def test_get_s3_storage_client_uses_settings():
    storage = get_s3_storage_client()

    assert await storage.get_file_url("k") == f"{settings.S3_PUBLIC_URL.rstrip('/')}/{settings.S3_BUCKET_NAME}/k"
