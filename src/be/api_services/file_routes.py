"""
File routes module for handling file-related API endpoints.

This module provides FastAPI route handlers for file operations including:
- File upload and download
- File metadata management 
- File status tracking
- Question generation from file content

The module integrates with storage, database and Redis services to provide
a complete file management system with async processing capabilities.
"""

import hashlib
import asyncio
import re
import os
import time
import uuid
from typing import List
from urllib.parse import quote
import json

from pydantic import BaseModel
from fastapi import APIRouter
from fastapi import Depends, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from openai import AsyncOpenAI

from be.common.database_manager import FileMetadata, Chunk
from be.common.file_metadata_response import FileMetadataResponse
from be.common.redis_manager import RedisManager
from be.common.storage_manager import StorageManager
from be.common.exceptions import StorageError, DatabaseError, RedisError
from be.llm_knowledge_processing.knowledge_processing_service import KnowledgeProcessingService
from be.api_services.shared_resources import (
    db_manager,
    redis_manager,
    storage_manager,
    background_tasks,
    MAX_CONCURRENT_TASKS,
    get_logger
)

logger = get_logger()
running_services = set()
# Create an APIRouter instance
router = APIRouter()

async def get_db():
    """
    Dependency function that yields a database session.
    
    This function initializes the database engine if not already initialized,
    and yields database sessions for use in FastAPI endpoints.
    
    Yields:
        AsyncSession: An async SQLAlchemy database session
    """
    async with db_manager.get_db() as db:
        yield db

async def get_redis_manager() -> RedisManager:
    """
    Dependency function that initializes and returns a Redis manager instance.
    
    This function ensures the Redis manager is initialized before returning it
    for use in FastAPI endpoints.
    
    Returns:
        RedisManager: An initialized Redis manager instance
    """
    return redis_manager

async def get_storage_manager() -> StorageManager:
    """
    Dependency function that initializes and returns a storage manager instance.
    
    This function ensures the storage manager is initialized before returning it
    for use in FastAPI endpoints.
    
    Returns:
        StorageManager: An initialized storage manager instance
    """
    return storage_manager

@router.post("/upload/{user_id}")
async def upload_file(
    user_id: str,
    file: UploadFile = File(...),
    db_mgr: AsyncSession = Depends(get_db),
    redis_mgr: RedisManager = Depends(get_redis_manager),
    storage_mgr: StorageManager = Depends(get_storage_manager)
):
    """
    Upload a file for a specific user.

    This endpoint handles file upload by:
    1. Checking if file already exists using file_id
    2. Storing file content in object storage
    3. Saving file metadata to database
    4. Managing file status in Redis

    Args:
        user_id (str): ID of the user uploading the file
        file (UploadFile): The file to be uploaded
        db_mgr (AsyncSession): Database session for metadata operations
        redis_mgr (RedisManager): Redis manager for status tracking
        storage_mgr (StorageManager): Storage manager for file content

    Returns:
        dict: A dictionary containing:
            - file_id (str): Unique identifier for the file
            - filename (str): Original name of the file
            - size (int): File size in bytes
            - type (str): File content type
            - upload_time (str): ISO formatted upload timestamp
            - stored_filename (str): Name used to store the file
            - status (str): Upload status message

    Raises:
        HTTPException: 
            - 500 if any storage, database or Redis operations fail
            - 500 for unexpected errors during upload
    """
    unique_string = f"{file.filename}-{user_id}"
    file_id = hashlib.sha256(unique_string.encode()).hexdigest()
    # 生成唯一的文件名，包含用户ID、文件ID和原始文件名
    stored_filename = f"{user_id}_{file_id}_{file.filename}"

    try:
        existing_file: FileMetadata = await db_manager.get_file_metadata_by_file_id(db_mgr, file_id)
        if existing_file:
            logger.warning(
                "File with file_id %s already exists. Returning existing file info.",
                file_id
            )
            return {
                "file_id": existing_file.file_id,
                "filename": existing_file.filename,
                "size": existing_file.file_size,
                "type": existing_file.file_type,
                "upload_time": existing_file.upload_time.isoformat(),
                "stored_filename": existing_file.stored_filename,
                "status": "File Already exists"
            }

        await redis_mgr.set_file_status(file_id, "Pending")

        file_content = await file.read()
        file_content = filter_html_links(file_content)
        logger.debug("stored_filename: %s, user_id: %s", stored_filename, user_id)
        logger.debug("file_content size: %s", len(file_content))

        await storage_mgr.upload_file(file_content, stored_filename, user_id)

        file_metadata: FileMetadata = await db_manager.save_file_metadata(
            db=db_mgr,
            file_id=file_id,
            user_id=user_id,
            filename=file.filename,
            file_size= len(file_content) ,
            file_type=file.content_type,
            stored_filename=stored_filename
        )
        if not file_metadata:
            raise DatabaseError("Failed to save file metadata")

        return {
            "file_id": file_id,
            "filename": file.filename,
            "size": len(file_content),
            "type": file.content_type,
            "upload_time": file_metadata.upload_time.isoformat(),
            "stored_filename": stored_filename,
            "status": "Upload Completed"
        }
    except (RedisError, StorageError, DatabaseError) as e:
        logger.error(
            "File upload failed for file_id %s: %s",
            file_id,
            str(e),
            exc_info=True
        )
        await redis_mgr.delete_file_status(file_id)
        await storage_mgr.delete_file(stored_filename, user_id)
        await db_manager.delete_file_metadata(db_mgr, file_id)
        raise HTTPException(
            status_code=500,
            detail=f"File upload failed: {e}"
        ) from e
    finally:
        await file.close()

@router.get("/files/", response_model=List[FileMetadataResponse])
async def get_all_files(
    db_mgr: AsyncSession = Depends(get_db)
) -> List[FileMetadataResponse]:
    """
    Retrieve all files from the database.

    This endpoint fetches metadata for all files stored in the system,
    regardless of user ownership.

    Args:
        db_mgr (AsyncSession): Database session dependency injection

    Returns:
        List[FileMetadataResponse]: List of file metadata objects containing file details
    """
    try:
        file_metadata_list: List[FileMetadata] = await db_manager.get_all_file_metadata(db_mgr)
        if not file_metadata_list:
            raise DatabaseError("No files found in the database")
        logger.debug("Found %d files in the database", len(file_metadata_list))

        file_metadata_response: List[FileMetadataResponse] = [
            FileMetadataResponse(
                id              = file_metadata.id,
                file_id         = file_metadata.file_id,
                user_id         = file_metadata.user_id,
                filename        = file_metadata.filename,
                file_size       = file_metadata.file_size,
                file_type       = file_metadata.file_type,
                upload_time     = file_metadata.upload_time.isoformat(),
                stored_filename = file_metadata.stored_filename
            )
            for file_metadata in file_metadata_list
        ]
        return file_metadata_response or []
    except DatabaseError as e:
        logger.error("Failed to get all files: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e

@router.get("/files/{user_id}", response_model=List[FileMetadataResponse])
async def get_files_by_user(
    user_id: str,
    skip: int = 0,
    limit: int = 100,
    db_mgr: AsyncSession = Depends(get_db)
) -> List[FileMetadataResponse]:
    """
    Retrieve all files for a specific user with pagination support.

    This endpoint fetches file metadata from the database for the given user_id,
    with optional pagination parameters to limit the result set.

    Args:
        user_id (str): ID of the user whose files to retrieve
        skip (int, optional): Number of records to skip. Defaults to 0.
        limit (int, optional): Maximum number of records to return. Defaults to 100.
        db_mgr (AsyncSession): Database session dependency injection

    Returns:
        List[FileMetadataResponse]: List of file metadata objects containing file details

    Raises:
        HTTPException: 404 if no files are found for the given user_id
    """
    try:
        results: List[FileMetadata] = await db_manager.get_file_metadata_by_user_id(
            db=db_mgr,
            user_id=user_id,
            skip=skip,
            limit=limit
        )
        if not results:
            raise DatabaseError(f"User {user_id} has no files")
        logger.debug("Found %d files for user %s", len(results), user_id)

        file_metadata_response: List[FileMetadataResponse] = [
            FileMetadataResponse(
                id              = result.id,
                file_id         = result.file_id,
                user_id         = result.user_id,
                filename        = result.filename,
                file_size       = result.file_size,
                file_type       = result.file_type,
                upload_time     = result.upload_time.isoformat(),
                stored_filename = result.stored_filename
            )
            for result in results
        ]
        return file_metadata_response or []
    except DatabaseError as e:
        logger.error("Failed to get files for user %s: %s", user_id, str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e

@router.get("/files/{user_id}/{file_id}", response_model=FileMetadataResponse)
async def get_file_by_user_and_fileid(
    user_id: str,
    file_id: str,
    db_mgr: AsyncSession = Depends(get_db)
) -> FileMetadataResponse:
    """
    Retrieve file metadata for a specific user and file ID.

    This endpoint fetches file metadata from the database for the 
    given user_id and file_id combination.

    Args:
        user_id (str): ID of the user who owns the file
        file_id (str): Unique identifier of the file to retrieve
        db_mgr (AsyncSession): Database session dependency injection

    Returns:
        FileMetadataResponse: File metadata object containing file details

    Raises:
        HTTPException: 404 if no file is found for the given user_id and file_id
    """
    try:
        result: FileMetadata = await db_manager.get_file_metadata_by_userid_and_fileid(
            db=db_mgr,
            user_id=user_id,
            file_id=file_id
        )
        if not result:
            raise DatabaseError(f"File '{file_id}' not found for user {user_id}")
        logger.debug("Found file metadata for file_id %s", file_id)

        file_metadata_response: FileMetadataResponse = FileMetadataResponse(
            id              = result.id,
            file_id         = result.file_id,
            user_id         = result.user_id,
            filename        = result.filename,
            file_size       = result.file_size,
            file_type       = result.file_type,
            upload_time     = result.upload_time.isoformat(),
            stored_filename = result.stored_filename
        )
        return file_metadata_response
    except DatabaseError as e:
        logger.error("Failed to get file metadata for file_id %s: %s", file_id, str(e))
        raise HTTPException(status_code=404, detail="Internal server error") from e

@router.delete("/delete/{user_id}/{file_id}")
async def delete_file(
    user_id: str,
    file_id: str,
    db_mgr: AsyncSession = Depends(get_db),
    redis_mgr: RedisManager = Depends(get_redis_manager),
    storage_mgr: StorageManager = Depends(get_storage_manager)
):
    """
    Delete a file and its associated metadata for a specific user.

    This endpoint performs the following operations:
    1. Verifies file exists for the given user
    2. Deletes the file from storage
    3. Removes file metadata from database
    4. Cleans up file status from Redis

    Args:
        user_id (str): ID of the user who owns the file
        file_id (str): Unique identifier of the file to delete
        db_mgr (AsyncSession): Database session for metadata operations
        redis_mgr (RedisManager): Redis manager for status cleanup
        storage_mgr (StorageManager): Storage manager for file deletion

    Returns:
        dict: A message confirming successful deletion containing:
            - message (str): Success message with filename

    Raises:
        HTTPException: 
            - 404 if file not found
            - 500 for internal server errors during deletion
        FileNotFoundError: If file metadata not found
        DatabaseError: If database operations fail
        RedisError: If Redis operations fail
    """
    try:
        file_metadata: FileMetadata = await db_manager.get_file_metadata_by_userid_and_fileid(
            db=db_mgr,
            user_id=user_id,
            file_id=file_id
        )
        if not file_metadata:
            logger.error(
                "File with file_id %s not found for deletion.",
                file_id
            )
            raise DatabaseError(
                f"File with ID {file_id} not found for user {user_id}"
            )
        logger.debug("Found file metadata for file_id %s", file_id)

        await storage_mgr.delete_file(file_metadata.stored_filename, user_id)
        logger.debug(
            "Deleted file %s from storage for file_id %s.",
            file_metadata.stored_filename,
            file_id
        )

        chunks: List[Chunk] = await db_manager.get_chunks_by_file_id(db_mgr, file_id)
        for chunk in chunks:
            await db_manager.delete_questions_by_chunk_id(db_mgr, chunk.id)
        await db_manager.delete_chunks_by_file_id(db_mgr, file_id)
        await db_manager.delete_file_metadata(
            db=db_mgr,
            file_id=file_id
        )
        logger.debug("Deleted file metadata for file_id %s from MySQL.", file_id)

        await redis_mgr.delete_file_status(file_id)
        logger.debug("Deleted file status for file_id %s from Redis.", file_id)

        return {"message": f"File {file_metadata.filename} deleted successfully"}
    except Exception as e:
        await db_mgr.rollback()
        logger.error("Failed to delete file with file_id %s: %s", file_id, str(e))
        raise HTTPException(
            status_code=404,
            detail=f"Internal server error: {str(e)}"
        ) from e

@router.get("/file_status/{file_id}")
async def redis_file_status(
    file_id: str,
    redis_mgr: RedisManager = Depends(get_redis_manager)
):
    """
    Get the processing status of a file from Redis.

    This endpoint retrieves the current processing status of a file from Redis using its file_id.
    The status indicates the current state of file processing 
    (e.g., "Pending", "Processing", "Completed").

    Args:
        file_id (str): The unique identifier of the file to check status for
        redis_mgr (RedisManager): Redis manager instance for accessing Redis storage

    Returns:
        dict: A dictionary containing:
            - file_id (str): The input file ID
            - status (str): Current processing status of the file

    Raises:
        HTTPException: 404 if no status is found for the given file_id
    """
    try:
        status = await redis_mgr.get_file_status(file_id)
        if status is None:
            raise RedisError(f"File status not found for file_id {file_id}")
        return {"file_id": file_id, "status": status}
    except RedisError as e:
        logger.error("Failed to get file status from Redis: %s", str(e))
        raise HTTPException(
            status_code=404, 
            detail="Internal server error - Failed to get file status from Redis"
        ) from e

@router.get("/download/{user_id}/{file_id}")
async def download_file(
    user_id: str,
    file_id: str,
    db_mgr: AsyncSession = Depends(get_db),
    storage_mgr: StorageManager = Depends(get_storage_manager)
):
    """
    Download a file for a specific user.

    This endpoint retrieves file metadata from the database and streams the file content
    from storage for download. The file name is URL encoded to handle special characters.

    Args:
        user_id (str): ID of the user requesting the file
        file_id (str): Unique identifier of the file to download
        db_mgr (AsyncSession): Database session dependency injection

    Returns:
        StreamingResponse: A streaming response containing:
            - File content as a stream
            - Content-Type header matching the file's type
            - Content-Disposition header for download with encoded filename

    Raises:
        HTTPException: 404 if the file is not found for the given user_id and file_id
    """
    try:
        file_metadata = await db_manager.get_file_metadata_by_userid_and_fileid(
            db=db_mgr,
            user_id=user_id,
            file_id=file_id
        )
        if not file_metadata:
            raise DatabaseError(f"File metadata not found for file_id {file_id}")
        logger.debug("Found file metadata for file_id %s", file_id)

        object_stream = await storage_mgr.download_file(
            file_metadata.stored_filename,
            user_id
        )
        object_stream.seek(0)
        encoded_filename = quote(file_metadata.filename)
        logger.debug("Downloading file %s from storage.", file_metadata.stored_filename)
        logger.debug("File content length: %d bytes", object_stream.getbuffer().nbytes)

        return StreamingResponse(
            content=object_stream,
            media_type=file_metadata.file_type,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
    except Exception as e:
        logger.error("Failed to download file with file_id %s: %s", file_id, str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e

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
    try:
        running_services.add(service.file_id)
        logger.info("Job %s has started running.", service.file_id)
        await service.run()
    finally:
        running_services.discard(service.file_id)
        logger.info("Job %s has finished running.", service.file_id)
        await service.shutdown()

@router.post("/questions/generate/{user_id}/{file_id}")
async def generate_questions(
    user_id: str,
    file_id: str
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
    service = KnowledgeProcessingService(user_id, file_id)

    if file_id not in running_services:
        if len(background_tasks) < MAX_CONCURRENT_TASKS:
            task = asyncio.create_task(run_service(service))
            background_tasks.add(task)
            task.add_done_callback(background_tasks.discard)
            return {"message": f"Started processing for file_id: {file_id}"}
        else:
            return {"message": f"Max concurrent tasks reached, processing for file_id: {file_id}"}
    else:
        return {"message": f"Processing already started for file_id: {file_id}"}

@router.get("/questions/{file_id}")
async def get_questions_by_file(
    file_id: str,
    db_mgr: AsyncSession = Depends(get_db),
    redis_mgr: RedisManager = Depends(get_redis_manager)
):
    """
    Retrieve all questions associated with a specific file.

    This endpoint checks if file processing is completed via Redis status,
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
    try:
        # 首先检查文件状态
        status = await redis_mgr.get_file_status(file_id)
        if status != "Completed":
            raise RedisError(f"File processing not completed, current status: {status}")
        logger.debug("File processing completed, status: %s", status)

        # 获取文件关联的所有chunks
        chunks: List[Chunk] = await db_manager.get_chunks_by_file_id(db_mgr, file_id)
        if not chunks:
            raise DatabaseError(f"No chunks found for file_id {file_id}")
        logger.debug("Found %d chunks for file_id %s", len(chunks), file_id)
        # 收集所有问题
        all_questions = []
        for chunk in chunks:
            questions = await db_manager.get_questions_by_chunk_id(db_mgr, chunk.id)
            if not questions:
                raise DatabaseError(f"No questions found for chunk_id {chunk.id}")
            all_questions.extend([{
                "question_id": q.id,
                "question": q.question,
                "label": q.label,
                "chunk_id": chunk.id
            } for q in questions])
        logger.debug("Found %d questions for file_id %s", len(all_questions), file_id)
        return {"file_id": file_id, "questions": all_questions}
    except DatabaseError as e:
        logger.error("Failed to get questions for file_id %s: %s", file_id, str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e
    except RedisError as e:
        logger.error("Failed to get file status from Redis: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e

class LLMQueryRequest(BaseModel):
    """
    Request model for LLM query endpoints.

    This model defines the structure of requests made to LLM query endpoints,
    containing identifiers for both the question and its associated chunk context.

    Attributes:
        question_id (int): Unique identifier of the question to be answered
        chunk_id (int): Identifier of the chunk containing context for the question
    """
    question_id: int
    chunk_id: int

@router.post("/llm/query")
async def llm_query(
    payload: LLMQueryRequest,
    db_mgr: AsyncSession = Depends(get_db)
):
    """
    Process an LLM query request by retrieving context and generating a response.

    This endpoint handles LLM query requests by:
    1. Validating LLM configuration settings
    2. Retrieving chunk content and associated question
    3. Constructing prompts with context and question
    4. Making API calls to the LLM service
    
    Args:
        payload (LLMQueryRequest): Request payload containing chunk_id and question_id
        db_mgr (AsyncSession): Database session for retrieving chunks and questions

    Returns:
        dict: The raw response from the LLM API containing:
            - id: Unique identifier for the completion
            - object: Type of object returned
            - created: Timestamp of when the completion was created
            - model: Name of the model used
            - choices: List of completion choices
            - usage: Token usage statistics

    Raises:
        HTTPException:
            - 500 if LLM configuration is missing
            - 404 if chunk or question not found
            - 502 if upstream LLM API call fails
    """
    llm_url = os.getenv("LLM_API_URL", "https://api.siliconflow.cn/v1/")
    if not llm_url:
        logger.error("LLM_API_URL is not configured")
        raise HTTPException(status_code=500, detail="LLM_API_URL is not configured")

    llm_key = os.getenv("LLM_API_KEY", "sk-wkguetxfwibczehkadqilsphgxtumfilykwselnurzxfrskf")
    if not llm_key:
        logger.error("LLM_API_KEY is not configured")
        raise HTTPException(status_code=500, detail="LLM_API_KEY is not configured")

    model = os.getenv("LLM_MODEL", "deepseek-ai/DeepSeek-V3.1")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.4"))
    max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "5120"))

    # Fetch chunk content
    chunk = await db_manager.get_chunk_by_id(db_mgr, payload.chunk_id)
    if not chunk:
        logger.error("Chunk not found: %s", payload.chunk_id)
        raise HTTPException(status_code=404, detail=f"Chunk not found: {payload.chunk_id}")

    # Fetch question under this chunk
    questions = await db_manager.get_questions_by_chunk_id(db_mgr, payload.chunk_id)
    target_q = next((q for q in questions if q.id == payload.question_id), None)
    if not target_q:
        logger.error("Question %s not found under chunk %s", payload.question_id, payload.chunk_id)
        raise HTTPException(status_code=404, detail=f"Question not found: {payload.question_id}")

    # 组织提示词
    system_prompt = (
        "You are a helpful assistant. Answer the question using the provided context. "
        "If the answer is not in the context, share your thoughts instead of saying 'I don't know'."
    )
    user_content = (
        f"Question:\n{target_q.question}\n\n"
        f"Context:\n{chunk.content or ''}"
    )

    # 初始化 OpenAI 异步客户端（可带 base_url）
    client = (AsyncOpenAI(api_key=llm_key, base_url=llm_url)
             if llm_url else AsyncOpenAI(api_key=llm_key))

    try:
        # 调用 Chat Completions
        completion = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # 原样返回上游 JSON（FastAPI 会自动转为 JSON）
        return completion.model_dump()

    except Exception as e:
        logger.error("OpenAI API request failed: %s", str(e), exc_info=True)
        raise HTTPException(status_code=502, detail="Upstream OpenAI API error") from e

@router.post("/llm/query/stream")
async def llm_query_stream(
    payload: LLMQueryRequest,
    db_mgr: AsyncSession = Depends(get_db)
):
    """
    Stream LLM responses for a given query request.

    This endpoint provides streaming responses from an LLM model by:
    1. Retrieving context from the specified chunk
    2. Finding the target question
    3. Constructing prompts with context and question
    4. Streaming responses from the LLM API

    Args:
        payload (LLMQueryRequest): Request payload containing chunk_id and question_id
        db_mgr (AsyncSession): Database session for retrieving chunks and questions

    Returns:
        StreamingResponse: Server-sent events stream containing:
            - LLM response chunks in OpenAI API format
            - Error messages if processing fails
            - [DONE] marker on completion

    Raises:
        HTTPException: 
            - 500 if LLM configuration is missing
            - 404 if chunk or question not found
            - 500 for other processing errors
    """
    llm_url = os.getenv("LLM_API_URL", "https://api.siliconflow.cn/v1/")
    if not llm_url:
        logger.error("LLM_API_URL is not configured")
        raise HTTPException(status_code=500, detail="LLM_API_URL is not configured")

    llm_key = os.getenv("LLM_API_KEY", "sk-wkguetxfwibczehkadqilsphgxtumfilykwselnurzxfrskf")
    if not llm_key:
        logger.error("LLM_API_KEY is not configured")
        raise HTTPException(status_code=500, detail="LLM_API_KEY is not configured")

    model = os.getenv("LLM_MODEL", "Qwen/Qwen3-30B-A3B-Thinking-2507")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "7680"))

    # 读取上下文
    chunk = await db_manager.get_chunk_by_id(db_mgr, payload.chunk_id)
    if not chunk:
        logger.error("Chunk not found: %s", payload.chunk_id)
        raise HTTPException(status_code=404, detail=f"Chunk not found: {payload.chunk_id}")

    questions = await db_manager.get_questions_by_chunk_id(db_mgr, payload.chunk_id)
    # 通过遍历查找，避免把 Column[int] 当作字典键类型
    target_q = None
    for q in questions:
        if getattr(q, "id", None) == payload.question_id:
            target_q = q
            break

    if not target_q:
        logger.error("Question %s not found under chunk %s", payload.question_id, payload.chunk_id)
        raise HTTPException(status_code=404, detail=f"Question not found: {payload.question_id}")

    system_prompt = (
        "You are a helpful assistant. Answer the question using the provided context. "
        "If the answer is not in the context, share your thoughts instead of saying 'I don't know'."
    )
    user_content = (
        f"Question:\n{target_q.question}\n\n"
        f"Context:\n{chunk.content or ''}"
    )

    client = (AsyncOpenAI(api_key=llm_key, base_url=llm_url) 
             if llm_url else AsyncOpenAI(api_key=llm_key))

    async def sse_event_stream():
        try:
            # 开启上游流式
            stream = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            async for part in stream:
                # 直接使用上游 OpenAI 返回的原生数据
                try:
                    # 将上游的 chunk 转换为字典并直接输出
                    chunk_data = part.model_dump()
                    yield f'data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n'
                except Exception as e:
                    logger.warning("Failed to serialize chunk: %s", str(e))
                    # 如果序列化失败，尝试提取基本信息
                    try:
                        choice = part.choices[0]
                        delta = getattr(choice, "delta", None)
                        text = getattr(delta, "content", None) if delta else None
                        finish_reason = getattr(choice, "finish_reason", None)
                        
                        # 构造最小化的兼容格式
                        fallback_data = {
                            "id": getattr(part, "id", f"chatcmpl-{uuid.uuid4().hex[:8]}"),
                            "object": "chat.completion.chunk",
                            "created": getattr(part, "created", int(time.time())),
                            "model": getattr(part, "model", model),
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {"content": text} if text else {},
                                    "finish_reason": finish_reason
                                }
                            ]
                        }
                        yield f'data: {json.dumps(fallback_data, ensure_ascii=False)}\n\n'
                    except Exception:
                        # 完全失败时跳过这个chunk
                        continue
            
            # OpenAI API 标准结束标记
            yield 'data: [DONE]\n\n'

        except Exception as e:
            logger.error("OpenAI streaming failed: %s", str(e), exc_info=True)
            # 使用简化的错误格式
            error_chunk_data = {
                "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "error"
                    }
                ],
                "error": {
                    "message": str(e),
                    "type": "api_error"
                }
            }
            yield f'data: {json.dumps(error_chunk_data, ensure_ascii=False)}\n\n'
            yield 'data: [DONE]\n\n'

    # SSE 必须的响应头（根据网关/代理可再优化）
    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",  # Nginx 如有，建议禁止缓冲，加速推送
    }
    return StreamingResponse(sse_event_stream(), media_type="text/event-stream", headers=headers)

def filter_html_links(content: bytes) -> bytes:
    """
    Filter out HTML links and URLs from byte content.

    This function removes various types of HTML links including:
    - <a> tags with href attributes
    - <link> tags with href attributes  
    - Direct HTTP/HTTPS URLs
    - www. prefixed URLs

    Args:
        content (bytes): The input content as bytes containing HTML/text to filter

    Returns:
        bytes: The filtered content with links removed, encoded as UTF-8 bytes

    Note:
        If any error occurs during filtering, the original content is returned unchanged
        and a warning is logged.
    """
    try:
        # 将字节内容转换为字符串
        text_content = content.decode('utf-8', errors='ignore')

        # 过滤HTML链接的正则表达式模式
        patterns = [
            r'<a\s+[^>]*href\s*=\s*["\'][^"\'>]*["\'][^>]*>.*?</a>',  # <a href="...">...</a>
            r'<link\s+[^>]*href\s*=\s*["\'][^"\'>]*["\'][^>]*/?>', # <link href="...">
            r'https?://[^\s<>"\'{|}|\\^`\[\]]+',  # 直接的HTTP/HTTPS链接
            r'www\.[^\s<>"\'{|}|\\^`\[\]]+',  # www开头的链接
        ]

        # 逐个应用过滤模式
        for pattern in patterns:
            text_content = re.sub(pattern, '', text_content, flags=re.IGNORECASE | re.DOTALL)

        # 清理多余的空白字符
        text_content = re.sub(r'\n\s*\n', '\n\n', text_content)  # 合并多个空行
        text_content = re.sub(r'[ \t]+', ' ', text_content)  # 合并多个空格

        # 转换回字节格式
        return text_content.encode('utf-8')

    except (ValueError, AttributeError, TypeError) as e:
        logger.warning("Error filtering HTML links: %s, returning original content", e)
        return content
