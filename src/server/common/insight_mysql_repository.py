"""
InsightMySQLRepository — production MySQL adapter for InsightRepository.

Adapted from the original DatabaseManager with minor cleanups.
"""

import os
from typing import List, Optional
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError

from server.common.models import Base, FileMetadata, Chunk, Question
from server.common.repository import InsightRepository
from server.common.exceptions import DatabaseError


class InsightMySQLRepository(InsightRepository):
    """MySQL-backed adapter implementing the full InsightRepository interface."""

    def __init__(self) -> None:
        self.database_url = (
            f"mysql+aiomysql://"
            f"{os.getenv('DB_USER', 'root')}:"
            f"{os.getenv('DB_PASSWORD', '123456')}@"
            f"{os.getenv('DB_HOST', '192.168.31.233')}/"
            f"{os.getenv('DB_NAME', 'insight_flow')}?charset=utf8mb4"
        )
        self.engine = None
        self.async_session = None
        self._tables_created = False

    # ── Lifecycle ──────────────────────────────────────────────

    async def initialize(self) -> None:
        if self.engine:
            return
        try:
            self.engine = create_async_engine(
                self.database_url, echo=False,
                pool_size=10, max_overflow=20, pool_timeout=30,
                pool_recycle=3600, pool_pre_ping=True,
            )
            self.async_session = async_sessionmaker(
                self.engine, expire_on_commit=False, class_=AsyncSession,
            )
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to initialize database: {e}") from e

    async def init_db(self) -> None:
        if self._tables_created:
            return
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            self._tables_created = True
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to create database tables: {e}") from e

    async def dispose_engine(self) -> None:
        if self.engine:
            await self.engine.dispose()

    @asynccontextmanager
    async def get_db(self):
        async with self.async_session() as db:
            try:
                yield db
            except SQLAlchemyError as e:
                await db.rollback()
                raise DatabaseError(f"Database session error: {e}") from e

    # ── File metadata ──────────────────────────────────────────

    async def save_file_metadata(
        self, db: AsyncSession, file_id: str, user_id: str,
        filename: str, file_size: int, file_type: str, stored_filename: str,
    ) -> FileMetadata:
        try:
            fm = FileMetadata(file_id=file_id, user_id=user_id, filename=filename,
                              file_size=file_size, file_type=file_type,
                              stored_filename=stored_filename)
            db.add(fm)
            await db.commit()
            await db.refresh(fm)
            return fm
        except SQLAlchemyError as e:
            await db.rollback()
            raise DatabaseError(f"Failed to save file metadata: {e}") from e

    async def get_file_metadata_by_file_id(
        self, db: AsyncSession, file_id: str,
    ) -> Optional[FileMetadata]:
        try:
            r = await db.execute(select(FileMetadata).filter(FileMetadata.file_id == file_id))
            return r.scalars().first()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get file by ID {file_id}: {e}") from e

    async def get_file_metadata_by_stored_filename(
        self, db: AsyncSession, stored_filename: str,
    ) -> Optional[FileMetadata]:
        try:
            r = await db.execute(select(FileMetadata).filter(FileMetadata.stored_filename == stored_filename))
            return r.scalars().first()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get file by stored name {stored_filename}: {e}") from e

    async def get_file_metadata_by_user_id(
        self, db: AsyncSession, user_id: str, skip: int = 0, limit: int = 100,
    ) -> List[FileMetadata]:
        try:
            r = await db.execute(select(FileMetadata).filter(FileMetadata.user_id == user_id).offset(skip).limit(limit))
            return r.scalars().all()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get files by user {user_id}: {e}") from e

    async def get_all_file_metadata(self, db: AsyncSession) -> List[FileMetadata]:
        try:
            r = await db.execute(select(FileMetadata))
            return r.scalars().all()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get all file metadata: {e}") from e

    async def get_file_metadata_by_userid_and_fileid(
        self, db: AsyncSession, user_id: str, file_id: str,
    ) -> Optional[FileMetadata]:
        try:
            r = await db.execute(
                select(FileMetadata).filter(
                    FileMetadata.user_id == user_id,
                    FileMetadata.file_id == file_id,
                ))
            return r.scalars().first()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get file {file_id} for user {user_id}: {e}") from e

    async def delete_file_metadata(self, db: AsyncSession, file_id: str) -> int:
        try:
            r = await db.execute(delete(FileMetadata).filter(FileMetadata.file_id == file_id))
            await db.commit()
            return r.rowcount
        except SQLAlchemyError as e:
            await db.rollback()
            raise DatabaseError(f"Failed to delete file metadata: {e}") from e

    # ── Chunks ──────────────────────────────────────────────────

    async def save_chunks(
        self, db: AsyncSession, chunks: list, user_id: str,
        file_id: str, file_name: str,
    ) -> List[Chunk]:
        try:
            new_chunks = []
            for c in chunks:
                new_chunks.append(Chunk(
                    user_id=user_id, file_id=file_id, file_name=file_name,
                    content=c["content"], summary=c.get("summary", ""),
                    size=len(c["content"]), name=c.get("heading", ""),
                ))
            db.add_all(new_chunks)
            await db.commit()
            return new_chunks
        except SQLAlchemyError as e:
            await db.rollback()
            raise DatabaseError(f"Failed to save chunks: {e}") from e

    async def get_chunk_by_id(self, db: AsyncSession, chunk_id: int) -> Optional[Chunk]:
        try:
            r = await db.execute(select(Chunk).filter(Chunk.id == chunk_id))
            return r.scalars().first()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get chunk {chunk_id}: {e}") from e

    async def get_chunks_by_file_id(self, db: AsyncSession, file_id: str) -> List[Chunk]:
        try:
            r = await db.execute(select(Chunk).filter(Chunk.file_id == file_id))
            return r.scalars().all()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get chunks for file {file_id}: {e}") from e

    async def get_chunks_by_file_ids(self, db: AsyncSession, file_ids: list) -> List[Chunk]:
        try:
            r = await db.execute(select(Chunk).filter(Chunk.file_id.in_(file_ids)))
            return r.scalars().all()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get chunks for files {file_ids}: {e}") from e

    async def delete_chunk_by_id(self, db: AsyncSession, chunk_id: str) -> int:
        try:
            r = await db.execute(delete(Chunk).filter(Chunk.id == chunk_id))
            await db.commit()
            return r.rowcount
        except SQLAlchemyError as e:
            await db.rollback()
            raise DatabaseError(f"Failed to delete chunk {chunk_id}: {e}") from e

    async def delete_chunks_by_file_id(self, db: AsyncSession, file_id: str) -> int:
        try:
            r = await db.execute(delete(Chunk).filter(Chunk.file_id == file_id))
            await db.commit()
            return r.rowcount
        except SQLAlchemyError as e:
            await db.rollback()
            raise DatabaseError(f"Failed to delete chunks for file {file_id}: {e}") from e

    # ── Questions ───────────────────────────────────────────────

    async def save_questions(
        self, db: AsyncSession, user_id: str, file_id: str,
        questions: list, chunk_id: str,
    ) -> int:
        try:
            new_qs = []
            for q in questions:
                new_qs.append(Question(
                    user_id=user_id, file_id=file_id, chunk_id=chunk_id,
                    question=q["question"], label=q.get("label", "uncategorized"),
                ))
            db.add_all(new_qs)
            await db.commit()
            return len(new_qs)
        except SQLAlchemyError as e:
            await db.rollback()
            raise DatabaseError(f"Failed to save questions: {e}") from e

    async def get_questions_by_chunk_id(self, db: AsyncSession, chunk_id: int) -> List[Question]:
        try:
            r = await db.execute(select(Question).filter(Question.chunk_id == chunk_id))
            return r.scalars().all()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get questions for chunk {chunk_id}: {e}") from e

    async def delete_questions_by_chunk_id(self, db: AsyncSession, chunk_id: str) -> int:
        try:
            r = await db.execute(delete(Question).filter(Question.chunk_id == chunk_id))
            await db.commit()
            return r.rowcount
        except SQLAlchemyError as e:
            await db.rollback()
            raise DatabaseError(f"Failed to delete questions for chunk {chunk_id}: {e}") from e
