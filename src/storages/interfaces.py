from abc import ABC, abstractmethod
from datetime import datetime
from typing import Union


class S3StorageInterface(ABC):

    @abstractmethod
    async def upload_file(
            self, file_name: str, file_data: Union[bytes, bytearray], content_type: str
    ) -> None:
        """
        Uploads a file to the storage.

        :param file_name: The name of the file to be stored.
        :param file_data: The file data in bytes.
        :param content_type: MIME type the file will be served with.
        :raises S3FileUploadError: if the upload fails.
        """

    @abstractmethod
    async def get_file_url(self, file_name: str) -> str:
        """
        Generate a public URL for a file stored in the S3-compatible storage.

        :param file_name: The name of the file stored in the bucket.
        :return: The full URL to access the file.
        """

    @abstractmethod
    async def delete_file(self, file_name: str) -> None:
        """
        Deletes a file from the storage. Deleting a missing file is not an error.

        :param file_name: Object key in the bucket.
        :raises S3FileDeleteError: if the storage call fails.
        """

    @abstractmethod
    async def list_files(self, prefix: str) -> list[tuple[str, datetime]]:
        """
        Lists all files whose key starts with the prefix, across all result pages.

        :param prefix: Key prefix to filter by, e.g. "avatars/".
        :return: (key, last_modified) pairs; last_modified is timezone-aware (UTC).
            An empty list if nothing matches.
        :raises S3FileListError: if the storage call fails.
        """

    @abstractmethod
    async def delete_files(self, keys: list[str]) -> None:
        """
        Deletes many files, batched by the storage's per-request limit.
        Deleting a missing file is not an error. An empty list makes no storage call.

        :param keys: Object keys in the bucket.
        :raises S3FileDeleteError: if a storage call fails or the storage reports
            that some keys could not be deleted. Batches sent before the failure
            stay deleted.
        """
