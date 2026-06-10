# be/api_services/shared_resources.py
"""
Shared resource lifecycle management for the API services.

All resource instances are stored on app.state during startup and retrieved
via FastAPI Depends() in route handlers, or passed explicitly to background
services.

Usage in routes:
    @router.post("/...")
    async def handler(
        db=Depends(get_database_manager),
        redis=Depends(get_redis_manager),
        storage=Depends(get_storage_manager),
        llm=Depends(get_llm_gateway),
    ): ...

Usage in background services (constructor injection):
    service = KnowledgeProcessingService(
        user_id=..., file_id=...,
        db_manager=request.app.state.db_manager,
        redis_manager=request.app.state.redis_manager,
    )
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from be.api_services.insight_logger import setup_logging, get_logger
from be.common.insight_mysql_repository import InsightMySQLRepository
from be.common.redis_manager import RedisManager
from be.common.storage_interface import StorageInterface
from be.common.oss_storage import OSSStorage
from be.common.local_storage import LocalStorage
from be.llm_knowledge_processing.llm_gateway import LLMGateway


async def init_resources(app: FastAPI):
    """Initialise database, Redis, storage, and LLM gateway during startup."""
    logger = get_logger()

    db_manager = InsightMySQLRepository()
    await db_manager.initialize()
    await db_manager.init_db()
    app.state.db_manager = db_manager
    logger.debug("Database initialized.")

    redis_manager = RedisManager()
    await redis_manager.initialize()
    app.state.redis_manager = redis_manager
    logger.debug("Redis initialized.")

    storage_type = os.getenv("STORAGE_TYPE", "local")
    if storage_type == "oss":
        storage_client: StorageInterface = OSSStorage(
            access_key_id=os.getenv("OSS_ACCESS_KEY_ID", ""),
            access_key_secret=os.getenv("OSS_ACCESS_KEY_SECRET", ""),
            endpoint=os.getenv("OSS_ENDPOINT", "http://oss-cn-hangzhou.aliyuncs.com"),
            bucket_name=os.getenv("OSS_BUCKET_NAME", ""),
        )
        await storage_client.init_oss()
    else:
        storage_client = LocalStorage(
            base_dir=os.getenv(
                "LOCAL_STORAGE_BASE_DIR", os.path.join(".", "upload_file")
            )
        )
    app.state.storage_manager = storage_client
    logger.debug("Storage initialized.")

    app.state.llm_gateway = LLMGateway()
    logger.debug("LLM Gateway initialized.")


async def close_resources(app: FastAPI):
    """Gracefully release database and Redis resources."""
    logger = get_logger()

    db_manager = getattr(app.state, "db_manager", None)
    if db_manager is not None and db_manager.engine:
        await db_manager.dispose_engine()
        logger.debug("Database engine disposed.")

    redis_manager = getattr(app.state, "redis_manager", None)
    if redis_manager is not None and redis_manager.redis_client:
        await redis_manager.close_redis()
        logger.debug("Redis connection closed.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan handler for startup and shutdown."""
    setup_logging(app, log_file="api_services.log", level=logging.DEBUG)
    logger = get_logger()

    await init_resources(app)
    logger.info("Application startup completed.")

    yield

    await close_resources(app)
    logger.info("Application shutdown completed.")


app = FastAPI(lifespan=lifespan)
