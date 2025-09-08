# be/api_services/shared_resources.py
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
from typing import Optional
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

# 使用小写变量名，避免被基于命名约定的静态检查当作“常量”
_logger: Optional[logging.Logger] = None


def get_logger(fastapi_app: Optional[FastAPI] = None) -> logging.Logger:
    """
    Get the global logger. On first call, if not initialized yet, you MUST pass
    the FastAPI app so we can initialize logging via setup_logging.
    Subsequent calls can omit the app and will return the cached logger.

    Raises:
        RuntimeError: if the logger has not been initialized and no app is provided.
    """
    global _logger
    if _logger is not None:
        return _logger

    if fastapi_app is None:
        raise RuntimeError(
            "Logger not initialized. Call get_logger(fastapi_app) during application startup."
        )

    _logger = setup_logging(app=fastapi_app, log_file="api_services.log", level=logging.DEBUG)
    return _logger


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
async def lifespan(app: FastAPI):
    """
    Lifespan event handler that manages application startup and shutdown.
    
    This function replaces the deprecated @app.on_event("startup") and 
    @app.on_event("shutdown") decorators. It ensures that:
    - On startup: necessary resources (database, Redis, storage) are initialized
    - On shutdown: proper cleanup is performed
    """
    # Initialize logging once with the concrete FastAPI app
    logger = get_logger(app)

    # Startup
    await init_resources()
    logger.info("Application startup completed.")

    yield  # Application runs here

    # Shutdown
    await close_resources()
    logger.info("Application shutdown completed.")


# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)
logger = get_logger(app)
