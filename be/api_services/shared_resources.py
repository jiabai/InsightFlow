"""
Shared resources and initialization/cleanup utilities for the API services.

This module provides centralized resource management for database connections,
Redis client, storage, and background tasks. It includes functions for initializing
these resources when the FastAPI application starts and cleaning them up on shutdown.

Key components:
- Logger setup and access
- Database connection management
- Redis client management 
- Storage initialization
- Background task tracking
"""

import asyncio
import logging

from fastapi import FastAPI

from be.api_services.fastapi_logger import setup_logging
from be.common.database_manager import DatabaseManager
from be.common.redis_manager import RedisManager
from be.common.storage_manager import StorageManager

# Initialize FastAPI app
app = FastAPI()

LOGGER = None
def get_logger():
    global LOGGER
    if LOGGER is None:
        LOGGER = setup_logging(app=app, log_file='api_services.log', level=logging.DEBUG)
    return LOGGER

db_manager = DatabaseManager()
redis_manager = RedisManager()
storage_manager = StorageManager()

background_tasks = set()

async def init_resources():
    """在 FastAPI 启动阶段初始化数据库、Redis 与存储。"""
    if not db_manager.engine:
        await db_manager.initialize()
        await db_manager.init_db()

    await redis_manager.initialize()
    await storage_manager.init_storage()

async def close_resources():
    """在 FastAPI 关闭阶段统一释放资源。"""
    for task in background_tasks:
        task.cancel()
    await asyncio.gather(*background_tasks, return_exceptions=True)

    if db_manager.engine:
        await db_manager.dispose_engine()

    if redis_manager.redis_client:
        await redis_manager.close_redis()
