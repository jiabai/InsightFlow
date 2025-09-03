import io
import os
import oss2
from starlette.concurrency import run_in_threadpool
from be.common.storage_interface import StorageInterface
from be.common.exceptions import StorageError

class OSSStorage(StorageInterface):
    """
    阿里云OSS存储实现，继承自 StorageInterface。
    """
    def __init__(self, access_key_id: str, access_key_secret: str, endpoint: str, bucket_name: str):
        self.auth = oss2.Auth(access_key_id, access_key_secret)
        try:
            self.bucket = oss2.Bucket(self.auth, endpoint, bucket_name)
        except oss2.exceptions.OssError as e:
            raise StorageError(f"Failed to connect to OSS or invalid credentials: {e}") from e

    async def init_oss(self):
        """Asynchronously initializes the OSS connection by listing a single object to check 
        credentials."""
        try:
            # 尝试列举一个对象来检查连接和凭据
            # 注意：这可能会产生一个小的OSS请求费用
            await run_in_threadpool(lambda: list(self.bucket.list_objects(max_keys=1)))
        except oss2.exceptions.OssError as e:
            raise StorageError(f"Failed to connect to OSS or invalid credentials: {e}") from e

    async def upload_file(self, file_content: bytes, unique_filename: str, custom_dir: str = None):
        try:
            oss_path = f"{custom_dir}/{unique_filename}" if custom_dir else unique_filename
            await run_in_threadpool(self.bucket.put_object, oss_path, file_content)
        except oss2.exceptions.OssError as e:
            raise StorageError(f"Failed to upload file {unique_filename} to OSS: {e}") from e

    async def download_file(self, unique_filename: str, custom_dir: str = None) -> io.BytesIO:
        try:
            oss_path = f"{custom_dir}/{unique_filename}" if custom_dir else unique_filename
            response = await run_in_threadpool(self.bucket.get_object, oss_path)
            object_stream = io.BytesIO()
            object_stream.write(response.read())
            object_stream.seek(0)
            return object_stream
        except oss2.exceptions.OssError as e:
            if e.code == 'NoSuchKey':
                raise FileNotFoundError(f"File not found in OSS: {unique_filename}") from e
            raise StorageError(f"Failed to download file {unique_filename} from OSS: {e}") from e

    async def delete_file(self, unique_filename: str, custom_dir: str = None):
        try:
            oss_path = f"{custom_dir}/{unique_filename}" if custom_dir else unique_filename
            await run_in_threadpool(self.bucket.delete_object, oss_path)
        except oss2.exceptions.OssError as e:
            if e.code == 'NoSuchKey':
                # 如果文件不存在，我们认为删除操作成功，不抛出错误
                return
            raise StorageError(f"Failed to delete file {unique_filename} from OSS: {e}") from e
