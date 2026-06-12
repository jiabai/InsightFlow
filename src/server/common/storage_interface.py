from abc import ABC, abstractmethod
import io


def sanitize_path_component(component: str) -> str:
    """Reduce an untrusted string to a single safe path/key component.

    Strips any directory parts (handling both '/' and '\\' separators) so a
    crafted ``user_id`` or uploaded filename cannot use ``..`` or absolute
    paths to escape the storage base directory (local) or manipulate the
    object-key prefix (OSS). Applied identically on upload/download/delete so
    the resolved location stays consistent for a given stored value.
    """
    if not component:
        return "unnamed"
    last = component.replace("\\", "/").split("/")[-1].strip()
    if last in ("", ".", ".."):
        return "unnamed"
    return last


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
