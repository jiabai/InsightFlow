import os
from typing import Optional

from be.common.storage_interface import StorageInterface
from be.common.oss_storage import OSSStorage
from be.common.local_storage import LocalStorage

class StorageManager:
    """
    A manager class that handles file storage operations across different storage backends.

    This class provides a unified interface for file operations (upload, download, delete)
    while abstracting away the underlying storage implementation details. It supports
    multiple storage backends including local filesystem and Aliyun OSS, determined
    by environment configuration.

    The storage backend is selected based on the STORAGE_TYPE environment variable:
    - "local": Uses local filesystem storage
    - "oss": Uses Aliyun OSS (Object Storage Service)
    """
    def __init__(self, storage_type: Optional[str] = None):
        self.storage_type = storage_type or os.getenv("STORAGE_TYPE", "local")

        if self.storage_type == "oss":
            self.oss_access_key_id = os.getenv("OSS_ACCESS_KEY_ID", "your-access-key-id")
            self.oss_access_key_secret = os.getenv(
                "OSS_ACCESS_KEY_SECRET", "your-access-key-secret")
            self.oss_endpoint = os.getenv("OSS_ENDPOINT", "http://oss-cn-hangzhou.aliyuncs.com")
            self.oss_bucket_name = os.getenv("OSS_BUCKET_NAME", "your-bucket-name")
            self.storage_client: StorageInterface = OSSStorage(
                self.oss_access_key_id,
                self.oss_access_key_secret, 
                self.oss_endpoint,
                self.oss_bucket_name
            )
        elif self.storage_type == "local":
            self.local_storage_base_dir = os.getenv(
                "LOCAL_STORAGE_BASE_DIR", 
                os.path.join(".", "upload_file")
            )
            self.storage_client: StorageInterface = LocalStorage(self.local_storage_base_dir)
        else:
            raise ValueError("Invalid STORAGE_TYPE specified. Must be 'oss' or 'local'.")

    async def upload_file(self, file_content: bytes, stored_filename: str, custom_dir: str = None):
        await self.storage_client.upload_file(file_content, stored_filename, custom_dir)

    async def delete_file(self, stored_filename: str, custom_dir: str = None):
        await self.storage_client.delete_file(stored_filename, custom_dir)

    async def download_file(self, stored_filename: str, custom_dir: str = None):
        return await self.storage_client.download_file(stored_filename, custom_dir)

    async def init_storage(self):
        """Asynchronously initializes the chosen storage client."""
        if self.storage_type == "oss":
            await self.storage_client.init_oss()
