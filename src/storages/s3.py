from typing import Union
from urllib.parse import quote

import aioboto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from storages import S3StorageInterface
from exceptions.storages import S3FileUploadError, S3FileDeleteError


class S3StorageClient(S3StorageInterface):

    def __init__(
            self,
            endpoint_url: str,
            public_url: str,
            access_key: str,
            secret_key: str,
            bucket_name: str
    ):
        self._endpoint_url = endpoint_url
        self._public_url = public_url.rstrip("/")
        self._bucket_name = bucket_name
        self._session = aioboto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        self._config = Config(s3={"addressing_style": "path"})

    async def upload_file(
            self, file_name: str, file_data: Union[bytes, bytearray], content_type: str
    ) -> None:
        try:
            async with self._session.client(
                    "s3", endpoint_url=self._endpoint_url, config=self._config
            ) as s3:
                await s3.put_object(
                    Bucket=self._bucket_name,
                    Key=file_name,
                    Body=file_data,
                    ContentType=content_type,
                )
        except (BotoCoreError, ClientError) as e:
            raise S3FileUploadError(f"Failed to upload {file_name}") from e

    async def delete_file(self, file_name: str) -> None:
        try:
            async with self._session.client(
                    "s3", endpoint_url=self._endpoint_url, config=self._config
            ) as s3:
                await s3.delete_object(Bucket=self._bucket_name, Key=file_name)
        except (BotoCoreError, ClientError) as e:
            raise S3FileDeleteError(f"Failed to delete {file_name}") from e

    async def get_file_url(self, file_name: str) -> str:
        return f"{self._public_url}/{self._bucket_name}/{quote(file_name)}"
