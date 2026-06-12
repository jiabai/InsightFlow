"""Question generation and retrieval."""

import hashlib
import asyncio
import re
import os
import time
import uuid
from typing import List
from urllib.parse import quote
import json
import traceback

from pydantic import BaseModel
from fastapi import APIRouter, Request
from fastapi import Depends, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from server.common.models import FileMetadata, Chunk
from server.common.repository import InsightRepository
from server.common.file_metadata_response import FileMetadataResponse
from server.common.file_status_store import FileStatusStore
from server.common.storage_interface import StorageInterface
from server.common.exceptions import StorageError, DatabaseError, StatusStoreError
from server.api_services.shared_resources import get_logger

from server.llm_knowledge_processing.knowledge_processing_service import KnowledgeProcessingService
from server.llm_knowledge_processing.llm_gateway import LLMGateway

running_services = set()
background_tasks = set()
DEFAULT_MAX_CONCURRENT_TASKS = 10
router = APIRouter()


def get_max_concurrent_tasks() -> int:
    """Return the configured background question generation concurrency limit."""
    raw_limit = os.getenv("INSIGHTFLOW_MAX_CONCURRENT_TASKS", str(DEFAULT_MAX_CONCURRENT_TASKS))
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        return DEFAULT_MAX_CONCURRENT_TASKS
    return limit if limit > 0 else DEFAULT_MAX_CONCURRENT_TASKS


async def get_database_manager(request: Request) -> InsightRepository:
    """Dependency that returns the shared InsightRepository instance."""
    return request.app.state.db_manager

async def get_db(request: Request):
    """Dependency that yields a database session."""
    db_mgr: InsightRepository = request.app.state.db_manager
    async with db_mgr.get_db() as db:
        yield db

async def get_status_store(request: Request) -> FileStatusStore:
    """Dependency that returns the shared file status store instance."""
    return request.app.state.status_store

async def get_storage_manager(request: Request) -> StorageInterface:
    """Dependency that returns the shared StorageInterface instance."""
    return request.app.state.storage_manager


async def get_llm_gateway(request: Request) -> LLMGateway:
    """Dependency that returns the LLMGateway."""
    return request.app.state.llm_gateway

async def run_service(service: KnowledgeProcessingService):
    """
    Run a KnowledgeProcessingService instance asynchronously and ensure proper shutdown.

    This function executes the service's run method and handles cleanup by calling
    shutdown in a finally block to ensure resources are properly released.

    Args:
        service (KnowledgeProcessingService): The service instance to run

    Returns:
        None

    Raises:
        Any exceptions raised by the service's run or shutdown methods
    """
    logger = get_logger()
    try:
        running_services.add(service.file_id)
        logger.info("Job %s has started running. Current tasks: %d",
                   service.file_id, len(asyncio.all_tasks()))
        await service.run()
    finally:
        running_services.discard(service.file_id)
        logger.info("Job %s has finished running. Remaining tasks: %d",
                   service.file_id, len(asyncio.all_tasks()))
        await service.shutdown()

@router.post("/questions/generate/{user_id}/{file_id}")
async def generate_questions(
    user_id: str,
    file_id: str,
    request: Request,
    db_mgr: InsightRepository = Depends(get_database_manager),
    status_store: FileStatusStore = Depends(get_status_store),
):
    """
    Generate questions for a specific file asynchronously.

    This endpoint initiates asynchronous question generation for a file by:
    1. Creating a KnowledgeProcessingService instance
    2. Running the service as a background task
    3. Adding task to background tasks set for tracking

    Args:
        user_id (str): ID of the user who owns the file
        file_id (str): Unique identifier of the file to generate questions for

    Returns:
        dict: A dictionary containing:
            - message (str): Confirmation message with file_id

    Note:
        The actual question generation happens asynchronously in the background.
        Use the /questions/{file_id} endpoint to retrieve generated questions.
    """
    logger = get_logger()
    logger.debug(
        "questions generate request user_id=%s file_id=%s running=%s background_tasks=%d",
        user_id,
        file_id,
        file_id in running_services,
        len(background_tasks),
    )
    service = KnowledgeProcessingService(
        user_id=user_id,
        file_id=file_id,
        db_manager=db_mgr,
        status_store=status_store,
    )

    if file_id not in running_services:
        max_concurrent_tasks = get_max_concurrent_tasks()
        if len(background_tasks) < max_concurrent_tasks:
            task_name = f"run_service:{file_id}"
            task = asyncio.create_task(run_service(service), name=task_name)
            background_tasks.add(task)

            logger.info("Async task created: %s (total=%d)", task.get_name(), len(asyncio.all_tasks()))

            def _on_done(t: asyncio.Task):
                try:
                    exc = t.exception()
                except asyncio.CancelledError:
                    logger.info("Async task cancelled: %s", t.get_name())
                    return
                if exc:
                    logger.error("Async task errored: %s -> %r\n%s",
                                 t.get_name(), exc, "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
                else:
                    logger.info("Async task finished: %s", t.get_name())

            task.add_done_callback(_on_done)
            task.add_done_callback(background_tasks.discard)

            if os.getenv("DEBUG_ASYNCIO_DUMP_ON_GENERATE", "0") in ("1", "true", "yes"):
                dump_asyncio_tasks(prefix=f"[{task_name}]")

            return {"message": f"Processing request issued for file_id: {file_id}"}
        else:
            logger.warning(
                "questions generate backpressure file_id=%s background_tasks=%d max=%d",
                file_id,
                len(background_tasks),
                max_concurrent_tasks,
            )
            return {"message": f"Max concurrent tasks reached, processing for file_id: {file_id}"}
    else:
        logger.info("questions generate already running file_id=%s", file_id)
        return {"message": f"Processing already started for file_id: {file_id}"}

def dump_asyncio_tasks(prefix: str = "") -> None:
    """
    将当前事件循环中的任务状态打印到日志（仅用于临时排查）。
    """
    logger = get_logger()
    tasks = asyncio.all_tasks()
    logger.info("%s Dumping %d asyncio tasks...", prefix, len(tasks))
    for i, t in enumerate(tasks, 1):
        name = t.get_name() if hasattr(t, "get_name") else "<unnamed>"
        logger.info("%s [%d] %s - done=%s cancelled=%s coro=%r",
                    prefix, i, name, t.done(), t.cancelled(), getattr(t, "get_coro", lambda: None)())
        # 如需堆栈，可取消下方注释（注意日志量）
        # for f in t.get_stack(limit=5):
        #     logger.info("%s    stack: %s:%s in %s", prefix, f.f_code.co_filename, f.f_lineno, f.f_code.co_name)

@router.get("/questions/{file_id}")
async def get_questions_by_file(
    file_id: str,
    db_mgr: InsightRepository = Depends(get_database_manager),
    status_store: FileStatusStore = Depends(get_status_store)
):
    """
    Retrieve all questions associated with a specific file.

    This endpoint checks if file processing is completed via local status,
    then fetches all chunks associated with the file and their corresponding questions
    from the database.

    Args:
        file_id (str): The unique identifier of the file
        db_mgr (AsyncSession): Database session dependency injection

    Returns:
        dict: A dictionary containing:
            - file_id (str): The input file ID
            - questions (List[dict]): List of question objects, each containing:
                - question_id (int): Unique identifier of the question
                - question (str): The question text
                - label (str): The question label/category
                - chunk_id (int): ID of the chunk this question belongs to

    Raises:
        HTTPException: 
            - 400 if file processing is not completed
            - 404 if no chunks found for the file
    """
    logger = get_logger()
    try:
        # 首先检查文件状态
        logger.debug("questions fetch start file_id=%s", file_id)
        status = await status_store.get_file_status(file_id)
        if status != "Completed":
            raise StatusStoreError(f"File processing not completed, current status: {status}")
        logger.debug("questions fetch status file_id=%s status=%s", file_id, status)

        # 获取文件关联的所有chunks
        async with db_mgr.get_db() as db:
            chunks: List[Chunk] = await db_mgr.get_chunks_by_file_id(db, file_id)
            if not chunks:
                raise DatabaseError(f"No chunks found for file_id {file_id}")
            logger.debug("questions fetch chunks file_id=%s chunk_count=%d", file_id, len(chunks))
        # 收集所有问题
            all_questions = []
            for chunk in chunks:
                questions = await db_mgr.get_questions_by_chunk_id(db, chunk.id)
                if not questions:
                    raise DatabaseError(f"No questions found for chunk_id {chunk.id}")
                all_questions.extend([{
                    "question_id": q.id,
                    "question": q.question,
                    "label": q.label,
                    "chunk_id": chunk.id
                } for q in questions])
        logger.debug("questions fetch result file_id=%s question_count=%d", file_id, len(all_questions))
        return {"file_id": file_id, "questions": all_questions}
    except DatabaseError as e:
        logger.error("questions fetch database error file_id=%s error=%s", file_id, str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e
    except StatusStoreError as e:
        logger.error("questions fetch status error file_id=%s error=%s", file_id, str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


get_redis_manager = get_status_store

