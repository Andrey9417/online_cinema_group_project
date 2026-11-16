from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from botocore.exceptions import BotoCoreError, ClientError

from config.dependencies import get_s3_storage_client
from config.settings import settings
from exceptions.storages import S3FileDeleteError, S3FileListError, S3FileUploadError
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


def pages(*pages_, error=None):
    """Stands in for `paginator.paginate(...)`: an async iterator over result pages."""
    async def _gen():
        for page in pages_:
            yield page
        if error:
            raise error
    return _gen()


@pytest.fixture
def paginator(s3):
    """`get_paginator` is a plain (not awaited) method on the real client."""
    paginator = MagicMock()
    s3.get_paginator = MagicMock(return_value=paginator)
    return paginator


T1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
T2 = datetime(2026, 1, 2, tzinfo=timezone.utc)


async def test_list_files_merges_pages(storage, s3, paginator):
    paginator.paginate.return_value = pages(
        {"Contents": [{"Key": "avatars/1/a.png", "LastModified": T1}]},
        {"Contents": [{"Key": "avatars/2/b.png", "LastModified": T2}]},
    )

    result = await storage.list_files("avatars/")

    assert result == [("avatars/1/a.png", T1), ("avatars/2/b.png", T2)]
    s3.get_paginator.assert_called_once_with("list_objects_v2")
    paginator.paginate.assert_called_once_with(Bucket="bucket", Prefix="avatars/")


async def test_list_files_page_without_contents(storage, paginator):
    paginator.paginate.return_value = pages({"KeyCount": 0})

    assert await storage.list_files("avatars/") == []


@pytest.mark.parametrize("error", [client_error("ListObjectsV2"), BotoCoreError()])
async def test_list_files_error(storage, paginator, error):
    paginator.paginate.return_value = pages(
        {"Contents": [{"Key": "a.png", "LastModified": T1}]}, error=error
    )

    with pytest.raises(S3FileListError):
        await storage.list_files("avatars/")


async def test_delete_files(storage, s3):
    s3.delete_objects.return_value = {}

    await storage.delete_files(["a.png", "b.png"])

    s3.delete_objects.assert_awaited_once_with(
        Bucket="bucket",
        Delete={"Objects": [{"Key": "a.png"}, {"Key": "b.png"}], "Quiet": True},
    )


async def test_delete_files_batches_by_1000(storage, s3):
    s3.delete_objects.return_value = {}
    keys = [f"avatars/{i}.png" for i in range(2500)]

    await storage.delete_files(keys)

    batches = [call.kwargs["Delete"]["Objects"] for call in s3.delete_objects.await_args_list]
    assert [len(b) for b in batches] == [1000, 1000, 500]
    assert [o["Key"] for b in batches for o in b] == keys  # nothing lost or repeated
    storage._session.client.assert_called_once()  # one client for all batches


async def test_delete_files_empty_makes_no_call(storage, s3):
    await storage.delete_files([])

    storage._session.client.assert_not_called()
    s3.delete_objects.assert_not_called()


async def test_delete_files_reported_errors_raise(storage, s3):
    """S3 answers 200 with per-key `Errors`; those must not be silently ignored."""
    s3.delete_objects.return_value = {
        "Errors": [{"Key": "b.png", "Code": "AccessDenied", "Message": "nope"}]
    }

    with pytest.raises(S3FileDeleteError, match="b.png"):
        await storage.delete_files(["a.png", "b.png"])


async def test_delete_files_errors_in_first_batch_stop_the_rest(storage, s3):
    s3.delete_objects.side_effect = [
        {"Errors": [{"Key": "avatars/0.png", "Code": "InternalError", "Message": "x"}]},
        {},
        {},
    ]

    with pytest.raises(S3FileDeleteError):
        await storage.delete_files([f"avatars/{i}.png" for i in range(2500)])

    assert s3.delete_objects.await_count == 1


@pytest.mark.parametrize("error", [client_error("DeleteObjects"), BotoCoreError()])
async def test_delete_files_error(storage, s3, error):
    s3.delete_objects.side_effect = error

    with pytest.raises(S3FileDeleteError):
        await storage.delete_files(["a.png"])


async def test_get_s3_storage_client_uses_settings():
    storage = get_s3_storage_client()

    assert await storage.get_file_url("k") == f"{settings.S3_PUBLIC_URL.rstrip('/')}/{settings.S3_BUCKET_NAME}/k"
