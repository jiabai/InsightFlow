from abc import ABC, abstractmethod
import io

class StorageInterface(ABC):
    """
    定义存储服务接口的抽象基类。
    """
    @abstractmethod
    async def upload_file(self, file_content: bytes, unique_filename: str, custom_dir: str = None):
        pass

    @abstractmethod
    async def download_file(self, unique_filename: str, custom_dir: str = None) -> io.BytesIO:
        pass

    @abstractmethod
    async def delete_file(self, unique_filename: str, custom_dir: str = None):
        pass
