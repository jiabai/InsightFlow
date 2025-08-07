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
from contextlib import asynccontextmanager
from fastapi import FastAPI

from be.api_services.fastapi_logger import setup_logging
from be.common.database_manager import DatabaseManager
from be.common.redis_manager import RedisManager
from be.common.storage_manager import StorageManager

db_manager = DatabaseManager()
redis_manager = RedisManager()
storage_manager = StorageManager()

MAX_CONCURRENT_TASKS = 10
background_tasks = set()

LOGGER = None
def get_logger():
    global LOGGER
    if LOGGER is None:
        LOGGER = setup_logging(app=app, log_file='api_services.log', level=logging.DEBUG)
    return LOGGER

async def init_resources():
    """在 FastAPI 启动阶段初始化数据库、Redis 与存储。"""
    logger = get_logger()
    if not db_manager.engine:
        await db_manager.initialize()
        await db_manager.init_db()
        logger.debug("Database initialized.")
    else:
        logger.debug("Database engine already initialized.")

    await redis_manager.initialize()
    logger.debug("Redis initialized.")
    await storage_manager.init_storage()
    logger.debug("Storage initialized.")

async def close_resources():
    """在 FastAPI 关闭阶段统一释放资源。"""
    logger = get_logger()
    for task in background_tasks:
        task.cancel()
    await asyncio.gather(*background_tasks, return_exceptions=True)
    logger.debug("Background tasks canceled.")

    if db_manager.engine:
        await db_manager.dispose_engine()
        logger.debug("Database engine disposed.")
    else:
        logger.debug("Database engine not initialized.")

    if redis_manager.redis_client:
        await redis_manager.close_redis()

@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """
    Lifespan event handler that manages application startup and shutdown.
    
    This function replaces the deprecated @app.on_event("startup") and 
    @app.on_event("shutdown") decorators. It ensures that:
    - On startup: necessary resources (database, Redis, storage) are initialized
    - On shutdown: proper cleanup is performed
    """
    logger = get_logger()
    # Startup
    await init_resources()
    logger.info("Application startup completed.")

    yield  # Application runs here

    # Shutdown
    await close_resources()
    logger.info("Application shutdown completed.")

# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)
