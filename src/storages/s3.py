from typing import Union

import aioboto3

from storages import S3StorageInterface


class S3StorageClient(S3StorageInterface):

    def __init__(
            self,
            endpoint_url: str,
            access_key: str,
            secret_key: str,
            bucket_name: str
    ):
        self._endpoint_url = endpoint_url
        self._access_key = access_key
        self._secret_key = secret_key
        self._bucket_name = bucket_name

        self._session = aioboto3.Session(
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
        )

    async def upload_file(self, file_name: str, file_data: Union[bytes, bytearray]) -> None:
        pass

    async def get_file_url(self, file_name: str) -> str:
        pass
