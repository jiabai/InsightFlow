import io
import os
import aiofiles
import aiofiles.os
from be.common.storage_interface import StorageInterface
from be.common.exceptions import StorageError

class LocalStorage(StorageInterface):
    """
    本地文件存储实现，继承自 StorageInterface。
    文件存储在本地文件系统的指定目录下。
    """
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    async def upload_file(self, file_content: bytes, unique_filename: str, custom_dir: str = None):
        if custom_dir:
            target_dir = os.path.join(self.base_dir, custom_dir)
            os.makedirs(target_dir, exist_ok=True)
            file_path = os.path.join(target_dir, unique_filename)
        else:
            file_path = os.path.join(self.base_dir, unique_filename)

        try:
            async with aiofiles.open(file_path, mode="wb") as buffer:
                await buffer.write(file_content)
        except IOError as e:
            raise StorageError(f"Failed to upload file {unique_filename}: {e}") from e

    async def download_file(self, unique_filename: str, custom_dir: str = None) -> io.BytesIO:
        if custom_dir:
            file_path = os.path.join(self.base_dir, custom_dir, unique_filename)
        else:
            file_path = os.path.join(self.base_dir, unique_filename)
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            async with aiofiles.open(file_path, mode="rb") as f:
                content = await f.read()
                return io.BytesIO(content)
        except FileNotFoundError:
            raise
        except IOError as e:
            raise StorageError(f"Failed to download file {unique_filename}: {e}") from e

    async def delete_file(self, unique_filename: str, custom_dir: str = None):
        if custom_dir:
            file_path = os.path.join(self.base_dir, custom_dir, unique_filename)
        else:
            file_path = os.path.join(self.base_dir, unique_filename)
        try:
            if os.path.exists(file_path):
                await aiofiles.os.remove(file_path)
        except OSError as e:
            raise StorageError(f"Failed to delete file {unique_filename}: {e}") from e
