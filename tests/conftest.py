"""
Shared pytest fixtures for InsightFlow API tests.

Provides mock dependencies so tests never touch real services
(MySQL, Redis, OSS, external LLM APIs).

IMPORTANT: This module avoids importing shared_resources because
that triggers a chain of imports (RedisManager → aioredis) which
pulls in real infrastructure dependencies.
"""
import io
import os
import sys
import pytest
from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure src is on the Python path so 'be.*' imports work
_src = os.path.join(os.path.dirname(__file__), "..", "src")
_src = os.path.abspath(_src)
if _src not in sys.path:
    sys.path.insert(0, _src)

from be.common.insight_memory_repository import InsightMemoryRepository
from be.llm_knowledge_processing.llm_gateway import LLMGateway


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def memory_repo():
    """In-memory repository with no I/O — deterministic and fast."""
    return InsightMemoryRepository()


@pytest.fixture
def mock_llm_gateway():
    """LLMGateway in mock mode — returns preset responses, no API calls."""
    return LLMGateway(mock=True, mock_response="This is a mock answer.")


@pytest.fixture
def mock_redis():
    """Redis manager mock — no real Redis connection."""
    r = MagicMock()
    r.initialize = MagicMock()
    r.close_redis = MagicMock()
    # Make async methods return awaitables
    async def _get_status(fid):
        return "Completed"
    async def _set_status(fid, status, ttl=None):
        return True
    r.get_file_status = _get_status
    r.set_file_status = _set_status
    return r


@pytest.fixture
def mock_storage():
    """Storage interface mock — stores content in-memory."""
    s = MagicMock()
    async def _upload(content, filename, dir=None):
        return None
    async def _download(filename, dir=None):
        return io.BytesIO(b"mock file content")
    async def _delete(filename, dir=None):
        return None
    s.upload_file = _upload
    s.download_file = _download
    s.delete_file = _delete
    return s


def _install_overrides(app, memory_repo, mock_llm, mock_redis, mock_storage):
    """Install dependency overrides for all three route modules."""
    # Lazy import to avoid triggering RedisManager → aioredis import chain
    from be.api_services.file_routes import (
        get_database_manager as file_get_db_mgr,
        get_db as file_get_db,
        get_redis_manager as file_get_redis,
        get_storage_manager as file_get_storage,
    )
    from be.api_services.question_routes import (
        get_database_manager as q_get_db_mgr,
        get_db as q_get_db,
        get_redis_manager as q_get_redis,
        get_storage_manager as q_get_storage,
        get_llm_gateway as q_get_llm,
    )
    from be.api_services.llm_routes import (
        get_database_manager as llm_get_db_mgr,
        get_db as llm_get_db,
        get_redis_manager as llm_get_redis,
        get_storage_manager as llm_get_storage,
        get_llm_gateway as llm_get_llm,
    )

    overrides = {
        file_get_db_mgr: lambda: memory_repo,
        file_get_db: lambda: memory_repo,
        file_get_redis: lambda: mock_redis,
        file_get_storage: lambda: mock_storage,
        q_get_db_mgr: lambda: memory_repo,
        q_get_db: lambda: memory_repo,
        q_get_redis: lambda: mock_redis,
        q_get_storage: lambda: mock_storage,
        q_get_llm: lambda: mock_llm,
        llm_get_db_mgr: lambda: memory_repo,
        llm_get_db: lambda: memory_repo,
        llm_get_redis: lambda: mock_redis,
        llm_get_storage: lambda: mock_storage,
        llm_get_llm: lambda: mock_llm,
    }
    app.dependency_overrides.update(overrides)


@pytest.fixture
def test_app(memory_repo, mock_llm_gateway, mock_redis, mock_storage):
    """FastAPI app with all dependencies overridden to mocks.

    Uses a lifespan-free FastAPI instance so no real DB/Redis/Storage
    connections are attempted. Routers are registered and dependency
    overrides inject mock objects.
    """
    app = FastAPI()

    # Initialize the logger before importing any route modules, since
    # some of them call get_logger() at module level.
    from be.api_services.insight_logger import setup_logging
    setup_logging(app)

    # Lazy import to avoid triggering shared_resources module-level imports
    from be.api_services.file_routes import router as file_router
    from be.api_services.question_routes import router as question_router
    from be.api_services.llm_routes import router as llm_router

    app.include_router(file_router)
    app.include_router(question_router)
    app.include_router(llm_router)

    _install_overrides(app, memory_repo, mock_llm_gateway, mock_redis, mock_storage)
    return app


@pytest.fixture
def client(test_app):
    """FastAPI TestClient bound to the test app."""
    return TestClient(test_app)
