"""
File Management Service API endpoints.

This module provides FastAPI endpoints for managing file operations including:
- File upload and download
- File metadata management 
- File status tracking
- Question retrieval for processed files

The service integrates with:
- Object storage for file content
- Redis for status tracking
- Database for metadata and question storage

Key features:
- Secure file handling with user isolation
- Deduplication using file hashing
- Streaming file downloads
- Status tracking throughout file lifecycle
- Question generation and retrieval
"""

import hashlib
import logging
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from be.api_services.fastpai_logger import setup_logging
from be.common.database_manager import DatabaseManager, FileMetadata, Chunk
from be.common.redis_manager import RedisManager
from be.common.storage_manager import StorageManager
from be.common.exceptions import StorageError, DatabaseError, RedisError

# Create an APIRouter instance
router = APIRouter()

logger = setup_logging(None, log_file='file_management.log', level=logging.DEBUG)

db_manager = DatabaseManager()
async def get_db():
    """
    Dependency function that yields a database session.
    
    This function initializes the database engine if not already initialized,
    and yields database sessions for use in FastAPI endpoints.
    
    Yields:
        AsyncSession: An async SQLAlchemy database session
    """
    if not db_manager.engine:
        await db_manager.initialize()
        await db_manager.init_db()
    async with db_manager.get_db() as db:
        yield db

redis_manager = RedisManager()
async def get_redis_manager() -> RedisManager:
    """
    Dependency function that initializes and returns a Redis manager instance.
    
    This function ensures the Redis manager is initialized before returning it
    for use in FastAPI endpoints.
    
    Returns:
        RedisManager: An initialized Redis manager instance
    """
    await redis_manager.initialize()
    return redis_manager

storage_manager = StorageManager()
async def get_storage_manager() -> StorageManager:
    """
    Dependency function that initializes and returns a storage manager instance.
    
    This function ensures the storage manager is initialized before returning it
    for use in FastAPI endpoints.
    
    Returns:
        StorageManager: An initialized storage manager instance
    """
    await storage_manager.init_storage()
    return storage_manager

class FileMetadataResponse(BaseModel):
    """
    Pydantic model for file metadata response.
    
    This model defines the structure of file metadata that is returned by the API endpoints.
    It includes essential file information such as ID, name, size, type and timestamps.
    
    Attributes:
        id (int): Database record ID
        file_id (str): Unique file identifier
        user_id (str): ID of the user who owns the file
        filename (str): Original name of the file
        file_size (int): Size of the file in bytes
        file_type (Optional[str]): MIME type of the file
        upload_time (str): ISO formatted timestamp of when the file is uploaded
        stored_filename (str): Name under which the file is stored in the system
    """
    id: int
    file_id: str
    user_id: str
    filename: str
    file_size: int
    file_type: Optional[str] = None
    upload_time: str
    stored_filename: str

    class Config:
        """
        Configuration class for FileMetadataResponse model.
        
        This class enables ORM mode by setting from_attributes=True, allowing the model
        to work directly with SQLAlchemy ORM objects by automatically mapping 
        attributes from the ORM instance to the Pydantic model fields.
        """
        from_attributes = True

    @field_validator("upload_time", mode="before")
    @classmethod
    def format_upload_time(cls, value):
        """
        Format the upload time value to ISO format string.

        This validator ensures that datetime objects are converted to ISO format strings
        for consistent representation in API responses.

        Args:
            cls: The class reference (automatically provided by Pydantic)
            value: The upload time value to format, can be datetime or string

        Returns:
            str: The upload time in ISO format string
        """
        if isinstance(value, datetime):
            return value.isoformat()
        return value

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
    file_name = file.filename
    file_id = hashlib.sha256(file_name.encode()).hexdigest()

    result = await db_mgr.execute(
        select(FileMetadata).where(FileMetadata.file_id == file_id)
    )
    existing_file = result.scalars().first()
    if existing_file:
        logger.info(
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

    # 生成唯一的文件名，包含用户ID、文件ID和原始文件名
    stored_filename = f"{user_id}_{file_id}_{file_name}"

    try:
        try:
            await redis_mgr.set_file_status(file_id, "Pending")
        except Exception as e:
            raise RedisError(f"Failed to set file status in Redis: {e}") from e

        file_content = await file.read()
        try:
            await storage_mgr.upload_file(file_content, stored_filename, user_id)
        except Exception as e:
            raise StorageError(f"Failed to upload file to storage: {e}") from e

        try:
            await db_manager.save_file_metadata(
                db=db_mgr,
                file_id=file_id,
                user_id=user_id,
                filename=file.filename,
                file_size=file.size,
                file_type=file.content_type,
                stored_filename=stored_filename
            )
        except Exception as e:
            await db_mgr.rollback()
            raise DatabaseError(f"Failed to save file metadata to database: {e}") from e

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
        raise HTTPException(
            status_code=500,
            detail=f"File upload failed: {e}"
        ) from e
    except Exception as e:
        logger.error(
            "An unexpected error occurred during file upload for file_id %s: %s",
            file_id,
            str(e),
            exc_info=True
        )
        await redis_mgr.delete_file_status(file_id)
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {e}"
        ) from e
    finally:
        # 确保在任何情况下都关闭文件，尽管FastAPI通常会自动处理
        await file.close()

@router.get("/files/", response_model=List[FileMetadataResponse])
async def get_files(
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
    result = await db_mgr.execute(select(FileMetadata))
    return result.scalars().all()

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
    result = await db_manager.get_file_metadata_by_user_id(
        db=db_mgr,
        user_id=user_id,
        skip=skip,
        limit=limit
    )
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"User {user_id} has no files"
        )
    return result

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
    result = await db_manager.get_file_metadata_by_userid_and_fileid(
        db=db_mgr,
        user_id=user_id,
        file_id=file_id
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"File '{file_id}' not found for user {user_id}"
        )
    return result

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
        result = await db_mgr.execute(
            select(FileMetadata).filter(
                FileMetadata.file_id == file_id,
                FileMetadata.user_id == user_id
            )
        )
        file_metadata = result.scalars().first()
        if not file_metadata:
            logger.debug(
                "File with file_id %s not found for deletion.",
                file_id
            )
            raise FileNotFoundError(
                f"File with ID {file_id} not found for user {user_id}"
            )

        logger.debug("Found file metadata for file_id %s", file_id)

        await storage_mgr.delete_file(file_metadata.stored_filename, user_id)
        logger.debug("Deleted file %s from storage.", file_metadata.stored_filename)

        try:
            await db_manager.delete_file_metadata(
                db=db_mgr,
                file_id=file_id
            )
        except DatabaseError as db_err:
            await db_mgr.rollback()
            raise DatabaseError(
                f"Failed to delete file metadata in database: {db_err}"
            ) from db_err

        logger.debug("Deleted file metadata for file_id %s.", file_id)

        try:
            await redis_mgr.delete_file_status(file_id)
            logger.info("Deleted file status for file_id %s from Redis.", file_id)
        except RedisError as redis_err:
            logger.error(
                "Failed to delete file status for file_id %s from Redis: %s",
                file_id,
                str(redis_err)
            )

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
    status = await redis_mgr.get_file_status(file_id)
    if status is None:
        raise HTTPException(status_code=404, detail="File status not found in Redis")
    return {"file_id": file_id, "status": status}

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
    file_metadata = await db_manager.get_file_metadata_by_userid_and_fileid(
        db=db_mgr,
        user_id=user_id,
        file_id=file_id
    )
    if not file_metadata:
        raise HTTPException(status_code=404, detail="File not found")

    object_stream = await storage_manager.download_file(
        file_metadata.stored_filename,
        user_id
    )
    object_stream.seek(0)
    encoded_filename = quote(file_metadata.filename)

    return StreamingResponse(
        content=object_stream,
        media_type=file_metadata.file_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        }
    )

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
    # 首先检查文件状态
    await redis_manager.initialize()
    status = await redis_manager.get_file_status(file_id)
    if status != "Completed":
        raise HTTPException(
            status_code=400,
            detail=f"File processing not completed, current status: {status}"
        )
    logger.debug("File processing completed, status: %s", status)
    # 获取文件关联的所有chunks
    chunks: List[Chunk] = await db_manager.get_chunk_by_file_id(db_mgr, file_id)
    if not chunks:
        raise HTTPException(status_code=404, detail="No chunks found for this file")
    logger.debug("Found %d chunks for file_id %s", len(chunks), file_id)
    # 收集所有问题
    all_questions = []
    for chunk in chunks:
        questions = await db_manager.get_questions_by_chunk_id(db_mgr, chunk.id)
        all_questions.extend([{
            "question": q.question,
            "label": q.label,
            "chunk_id": chunk.id
        } for q in questions])
    logger.debug("Found %d questions for file_id %s", len(all_questions), file_id)
    return {"file_id": file_id, "questions": all_questions}
