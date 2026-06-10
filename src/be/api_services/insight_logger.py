"""
Unified InsightFlow logger supporting request context and task context.

Merges the three previous systems (fastapi_logger, logger_config, asyncio_logger)
into one module with a single setup_logging() entry point.

Usage:
    from be.api_services.insight_logger import get_logger, setup_logging
    setup_logging(app, log_file="api.log", level=logging.DEBUG)
    logger = get_logger()
"""

import logging
import uuid
import os
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import contextvars
import functools
from typing import Optional

from fastapi import FastAPI, Request

# ---------------------------------------------------------------------------
# Context variables — request and task metadata
# ---------------------------------------------------------------------------

url_var: contextvars.ContextVar[str] = contextvars.ContextVar("url", default="No_URL")
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="No_Request_ID"
)
task_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "task_id", default="No_Task"
)


def set_task_id(task_id: str) -> contextvars.Token:
    """Set a task ID for the current async context."""
    return task_id_var.set(task_id)


# ---------------------------------------------------------------------------
# Formatter
# ---------------------------------------------------------------------------

class InsightFlowFormatter(logging.Formatter):
    """Formatter that injects ContextVar values into every log record."""

    def format(self, record: logging.LogRecord) -> str:
        try:
            record.url = url_var.get()
            record.request_id = request_id_var.get()
            record.task_id = task_id_var.get()
        except LookupError:
            record.url = "No_URL"
            record.request_id = "No_Request_ID"
            record.task_id = "No_Task"
        return super().format(record)


# ---------------------------------------------------------------------------
# Singleton logger
# ---------------------------------------------------------------------------

_logger: Optional[logging.Logger] = None

DEFAULT_LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(url)s | "
    "r:%(request_id)s | t:%(task_id)s | "
    "%(pathname)s:%(funcName)s:%(lineno)d - %(message)s"
)


def get_logger() -> logging.Logger:
    """Return the unified InsightFlow logger.

    Raises RuntimeError if setup_logging() has not been called yet.
    """
    if _logger is None:
        raise RuntimeError(
            "Logger not initialized. Call setup_logging(app) during startup."
        )
    return _logger


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def setup_logging(
    app: FastAPI,
    log_file: str = "insight_flow.log",
    level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    rotation_type: str = "size",
    when: str = "midnight",
    use_console: bool = False,
) -> logging.Logger:
    """Configure the unified InsightFlow logger.

    Attaches a FastAPI middleware for request-context tracking.
    """
    global _logger

    logger = logging.getLogger("insightflow")
    logger.setLevel(level)

    # Prevent duplicate handlers
    if logger.handlers:
        logger.handlers.clear()

    formatter = InsightFlowFormatter(DEFAULT_LOG_FORMAT)

    # File handler
    log_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "logs"
    )
    os.makedirs(log_dir, exist_ok=True)
    full_path = os.path.join(log_dir, log_file)

    if rotation_type == "size":
        file_handler: logging.Handler = RotatingFileHandler(
            full_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
    elif rotation_type == "time":
        file_handler = TimedRotatingFileHandler(
            full_path, when=when, backupCount=backup_count
        )
    else:
        raise ValueError("rotation_type must be 'size' or 'time'")

    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    logger.addHandler(file_handler)

    # Console handler (optional, for local dev)
    if use_console:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        console.setLevel(level)
        logger.addHandler(console)

    # FastAPI request-context middleware
    @app.middleware("http")
    async def _insightflow_context_middleware(request: Request, call_next):
        request_id = uuid.uuid4().hex
        url = str(request.url)
        token_url = url_var.set(url)
        token_req = request_id_var.set(request_id)
        try:
            return await call_next(request)
        finally:
            url_var.reset(token_url)
            request_id_var.reset(token_req)

    _logger = logger
    return logger


# ---------------------------------------------------------------------------
# Async task context decorator
# ---------------------------------------------------------------------------

def with_task_id(func):
    """Decorator that sets task_id ContextVar for background tasks."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        tid = uuid.uuid4().hex[:8]
        token = task_id_var.set(tid)
        try:
            return await func(*args, **kwargs)
        finally:
            task_id_var.reset(token)

    return wrapper
