# server/api_services/shared_resources.py
"""
Shared resource lifecycle management for the API services.

All resource instances are stored on app.state during startup and retrieved
via FastAPI Depends() in route handlers, or passed explicitly to background
services.

Usage in routes:
    @router.post("/...")
    async def handler(
        db=Depends(get_database_manager),
        status_store=Depends(get_status_store),
        storage=Depends(get_storage_manager),
        llm=Depends(get_llm_gateway),
    ): ...

Usage in background services (constructor injection):
    service = KnowledgeProcessingService(
        user_id=..., file_id=...,
        db_manager=request.app.state.db_manager,
        status_store=request.app.state.status_store,
    )
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from server.api_services.insight_logger import setup_logging, get_logger
from server.common.insight_sqlite_repository import InsightSQLiteRepository
from server.common.file_status_store import FileStatusStore
from server.common.storage_interface import StorageInterface
from server.common.oss_storage import OSSStorage
from server.common.local_storage import LocalStorage
from server.llm_knowledge_processing.llm_gateway import LLMGateway


def _get_log_level() -> int:
    raw_level = os.getenv("INSIGHTFLOW_LOG_LEVEL", "DEBUG").upper()
    return getattr(logging, raw_level, logging.DEBUG)


def _get_log_console_enabled() -> bool:
    return os.getenv("INSIGHTFLOW_LOG_CONSOLE", "0").lower() in ("1", "true", "yes", "on")


async def init_resources(app: FastAPI):
    """Initialise database, file status store, storage, and LLM gateway."""
    logger = get_logger()

    db_manager = InsightSQLiteRepository()
    await db_manager.initialize()
    await db_manager.init_db()
    app.state.db_manager = db_manager
    logger.debug("Database initialized.")

    status_store = FileStatusStore()
    await status_store.initialize()
    app.state.status_store = status_store
    app.state.redis_manager = status_store
    logger.debug("Local file status store initialized.")

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
    """Gracefully release database and status store resources."""
    logger = get_logger()

    db_manager = getattr(app.state, "db_manager", None)
    if db_manager is not None and db_manager.engine:
        await db_manager.dispose_engine()
        logger.debug("Database engine disposed.")

    status_store = getattr(app.state, "status_store", None)
    if status_store is not None:
        await status_store.close()
        logger.debug("Local file status store closed.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan handler for startup and shutdown."""
    logger = get_logger()

    await init_resources(app)
    logger.info("Application startup completed.")

    yield

    await close_resources(app)
    logger.info("Application shutdown completed.")


def create_app(lifespan_handler=None):
    """Create a FastAPI application instance with an optional lifespan.

    Use this factory to create isolated app instances for testing::

        from server.api_services.shared_resources import create_app
        test_app = create_app(lifespan_handler=None)

    When ``lifespan_handler`` is None, the app starts without connecting
    to any databases or external services — suitable for unit tests
    that inject mock dependencies via ``app.dependency_overrides``.
    """
    application = FastAPI(lifespan=lifespan_handler)
    log_level = _get_log_level()
    log_to_console = _get_log_console_enabled()
    logger = setup_logging(
        application,
        log_file="api_services.log",
        level=log_level,
        use_console=log_to_console,
    )
    logger.info(
        "Logging configured level=%s console=%s",
        logging.getLevelName(log_level),
        log_to_console,
    )
    return application


app = create_app(lifespan_handler=lifespan)
