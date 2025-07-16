import hashlib
from datetime import datetime
from typing import List, Optional
import logging
from urllib.parse import quote

from fastapi import FastAPI, Depends, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from be.common.database_manager import DatabaseManager, FileMetadata
from be.common.redis_manager import RedisManager
from be.common.storage_manager import StorageManager
from be.common.logger_config import setup_logging
from be.common.exceptions import StorageError, DatabaseError, RedisError

# 初始化日志
setup_logging(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

db_manager = DatabaseManager()
async def get_db():
    if not db_manager.engine:
        await db_manager.initialize()
    async for db in db_manager.get_db():
        yield db

redis_manager = RedisManager()
async def get_redis_manager() -> RedisManager:
    await redis_manager.init_redis()
    return redis_manager

storage_manager = StorageManager()
async def get_storage_manager() -> StorageManager:
    await storage_manager.init_storage()
    return storage_manager

class FileMetadataResponse(BaseModel):
    """
    文件元数据响应模型，用于API返回文件信息。
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
        from_attributes = True

    @field_validator("upload_time", mode="before")
    @classmethod
    def format_upload_time(cls, value):
        if isinstance(value, datetime):
            return value.isoformat()
        return value

@app.post("/upload/{user_id}")
async def upload_file(
    user_id: str,
    file: UploadFile = File(...),
    db_mgr: AsyncSession = Depends(get_db),
    redis_mgr: RedisManager = Depends(get_redis_manager),
    storage_mgr: StorageManager = Depends(get_storage_manager)
):
    """
    上传文件接口，处理文件上传和元数据存储。

    :param user_id: 用户ID，用于关联文件元数据。
    :param file: 上传的文件对象。
    :param db: 数据库会话，用于元数据存储。
    :param redis_manager: Redis管理器，用于文件状态存储。
    :param storage_manager: 存储管理器，用于文件存储。
    :return: 上传成功后的文件信息。
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

@app.get("/files/", response_model=List[FileMetadataResponse])
async def get_files(db_mgr: AsyncSession = Depends(get_db)) -> List[FileMetadataResponse]:
    result = await db_mgr.execute(select(FileMetadata))
    return result.scalars().all()

@app.get("/files/{user_id}", response_model=List[FileMetadataResponse])
async def get_files_by_user(
    user_id: str,
    skip: int = 0,
    limit: int = 100,
    db_mgr: AsyncSession = Depends(get_db)
) -> List[FileMetadataResponse]:
    result = await db_manager.get_files_by_user_id(
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

@app.get("/files/{user_id}/{file_id}", response_model=FileMetadataResponse)
async def get_file_by_user_and_fileid(
    user_id: str,
    file_id: str,
    db_mgr: AsyncSession = Depends(get_db)
) -> FileMetadataResponse:
    result = await db_manager.get_file_by_userid_and_fileid(
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

@app.delete("/delete/{user_id}/{file_id}")
async def delete_file(
    user_id: str,
    file_id: str,
    db_mgr: AsyncSession = Depends(get_db),
    redis_mgr: RedisManager = Depends(get_redis_manager),
    storage_mgr: StorageManager = Depends(get_storage_manager)
):
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

@app.get("/file_status/{file_id}")
async def redis_file_status(
    file_id: str,
    redis_mgr: RedisManager = Depends(get_redis_manager)
):
    status = await redis_mgr.get_file_status(file_id)
    if status is None:
        raise HTTPException(status_code=404, detail="File status not found in Redis")
    return {"file_id": file_id, "status": status}

@app.get("/download/{user_id}/{file_id}")
async def download_file(
    user_id: str,
    file_id: str,
    db_mgr: AsyncSession = Depends(get_db)
):
    file_metadata = await db_manager.get_file_by_userid_and_fileid(
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

@app.get("/questions/{file_id}")
async def get_questions_by_file(
    file_id: str,
    db: AsyncSession = Depends(get_db)
):
    # 首先检查文件状态
    status = await redis_manager.get_file_status(file_id)
    if status != "Completed":
        raise HTTPException(
            status_code=400,
            detail=f"File processing not completed, current status: {status}"
        )

    # 获取文件关联的所有chunks
    chunks = db_manager.get_chunk_by_file_id(db, file_id)
    if not chunks:
        raise HTTPException(status_code=404, detail="No chunks found for this file")

    # 收集所有问题
    all_questions = []
    for chunk in chunks:
        questions = db_manager.get_questions_by_chunk_id(db, chunk.id)
        all_questions.extend([{
            "question": q.question,
            "label": q.label,
            "chunk_id": chunk.id
        } for q in questions])

    return {"file_id": file_id, "questions": all_questions}

@app.on_event("shutdown")
async def shutdown():
    if db_manager.engine:
        await db_manager.engine.dispose()
    if redis_manager.redis_client:
        await redis_manager.redis_client.close()
        await redis_manager.redis_client.wait_closed()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
