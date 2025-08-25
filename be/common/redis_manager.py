"""
Redis manager module for handling file status tracking.

This module provides a RedisManager class that interfaces with Redis for storing,
retrieving and managing file processing statuses. It uses Redis as a key-value store
where file IDs serve as keys for tracking their processing states.
"""
import os
import asyncio
import aioredis
from be.common.exceptions import RedisError

class RedisManager:
    """A class to manage Redis operations for file status tracking.

    This class provides an interface to interact with Redis for storing, retrieving,
    and managing file processing statuses. It handles basic Redis operations like
    setting, getting, and deleting file statuses using file IDs as keys.
    """
    def __init__(self):
        self.redis_host = os.getenv("REDIS_HOST", "192.168.31.233")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_client = None
        self._init_lock = asyncio.Lock()

    async def initialize(self):
        """Asynchronously initializes the Redis connection by pinging the server."""
        # 若已初始化且连接可用，直接返回
        if self.redis_client and not self.redis_client.closed:
            return
        # 若未初始化或连接已关闭，尝试重新初始化
        async with self._init_lock:
            # 再次检查，防止等待锁期间已被初始化
            if self.redis_client and not self.redis_client.closed:
                return
            try:
                self.redis_client = await aioredis.create_redis_pool(
                    f"redis://{self.redis_host}:{self.redis_port}",
                    minsize=1, maxsize=10,
                    encoding='utf-8'
                )
                response = await self.redis_client.ping()
                if response is False:
                    raise RedisError("Failed to ping Redis server.")
            except aioredis.ConnectionClosedError as e:
                raise RedisError(f"Failed to connect to Redis: {e}") from e
            except aioredis.RedisError as e:
                raise RedisError(f"Failed to initialize Redis: {e}") from e

    async def set_file_status(self, file_id: str, status: str, ttl_seconds: int = 604800):
        """Set the status of a file in Redis.

        Args:
            file_id (str): The unique identifier of the file whose status should be set.
            status (str): The status to set for the file.
        """
        try:
            await self.redis_client.set(file_id, ttl_seconds, status)
        except aioredis.RedisError as e:
            raise RedisError(f"Failed to set file status for {file_id}: {e}") from e

    async def get_file_status(self, file_id: str) -> str:
        """Get the status of a file from Redis.

        Args:
            file_id (str): The unique identifier of the file whose status should be retrieved.

        Returns:
            str: The status of the file if found, None if the file_id doesn't exist.
        """
        try:
            return await self.redis_client.get(file_id)
        except aioredis.RedisError as e:
            raise RedisError(f"Failed to get file status for {file_id}: {e}") from e

    async def delete_file_status(self, file_id: str):
        """Delete the status of a file from Redis.

        Args:
            file_id (str): The unique identifier of the file whose status should be deleted.
        """
        try:
            await self.redis_client.delete(file_id)
        except aioredis.RedisError as e:
            raise RedisError(f"Failed to delete file status for {file_id}: {e}") from e

    async def close_redis(self):
        """Asynchronously close the Redis connection."""
        if self.redis_client:
            self.redis_client.close()
            await self.redis_client.wait_closed()
