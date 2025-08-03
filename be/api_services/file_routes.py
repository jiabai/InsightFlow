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
from datetime import datetime
from typing import List
from urllib.parse import quote

from fastapi import APIRouter
from fastapi import Depends, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

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
    get_logger
)

logger = get_logger()

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
        logger.debug("stored_filename: %s, user_id: %s", stored_filename, user_id)
        logger.debug("file_content size: %s", len(file_content))

        await storage_mgr.upload_file(file_content, stored_filename, user_id)

        file_metadata: FileMetadata = await db_manager.save_file_metadata(
            db=db_mgr,
            file_id=file_id,
            user_id=user_id,
            filename=file.filename,
            file_size=file.size,
            file_type=file.content_type,
            stored_filename=stored_filename
        )
        if not file_metadata:
            raise DatabaseError("Failed to save file metadata")

        return {
            "file_id": file_id,
            "filename": file.filename,
            "size": file.size,
            "type": file.content_type,
            "upload_time": datetime.now().isoformat(),
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
        return file_metadata_response
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
        return file_metadata_response
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
        raise HTTPException(status_code=500, detail="Internal server error") from e

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
            status_code=500,
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
        raise HTTPException(status_code=500, detail="Internal server error") from e

@router.get("/download/{user_id}/{file_id}")
async def download_file(
    user_id: str,
    file_id: str,
    db_mgr: AsyncSession = Depends(get_db)
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

        object_stream = await storage_manager.download_file(
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
        await service.run()
    finally:
        await service.shutdown()

running_services = set()

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
    service = KnowledgeProcessingService(file_id)
    if file_id not in running_services:
        running_services.add(file_id)
        task = asyncio.create_task(run_service(service))
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)
    return {"message": f"Started processing for file_id: {file_id}"}

@router.get("/questions/{file_id}")
async def get_questions_by_file(
    file_id: str,
    db_mgr: AsyncSession = Depends(get_db)
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
        await redis_manager.initialize()
        status = await redis_manager.get_file_status(file_id)
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
