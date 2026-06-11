"""
InsightSQLiteRepository - production SQLite adapter for InsightRepository.

SQLite is the default local persistence layer for InsightFlow. The database
file is controlled by SQLITE_DB_PATH and defaults to data/insight_flow.sqlite3.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

from sqlalchemy import delete, event, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from server.common.exceptions import DatabaseError
from server.common.models import Base, Chunk, FileMetadata, Question
from server.common.repository import InsightRepository


DEFAULT_SQLITE_DB_PATH = Path("data") / "insight_flow.sqlite3"


class InsightSQLiteRepository(InsightRepository):
    """SQLite-backed adapter implementing the full InsightRepository interface."""

    def __init__(self) -> None:
        configured_path = os.getenv("SQLITE_DB_PATH")
        self.db_path = Path(configured_path or DEFAULT_SQLITE_DB_PATH).expanduser()
        self.database_url = f"sqlite+aiosqlite:///{self.db_path.resolve().as_posix()}"
        self.engine = None
        self.async_session = None
        self._tables_created = False

    async def initialize(self) -> None:
        if self.engine:
            return
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.engine = create_async_engine(self.database_url, echo=False)

            @event.listens_for(self.engine.sync_engine, "connect")
            def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

            self.async_session = async_sessionmaker(
                self.engine,
                expire_on_commit=False,
                class_=AsyncSession,
            )
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to initialize database: {e}") from e
        except OSError as e:
            raise DatabaseError(f"Failed to prepare SQLite database path: {e}") from e

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

    async def save_file_metadata(
        self,
        db: AsyncSession,
        file_id: str,
        user_id: str,
        filename: str,
        file_size: int,
        file_type: str,
        stored_filename: str,
    ) -> FileMetadata:
        try:
            fm = FileMetadata(
                file_id=file_id,
                user_id=user_id,
                filename=filename,
                file_size=file_size,
                file_type=file_type,
                stored_filename=stored_filename,
            )
            db.add(fm)
            await db.commit()
            await db.refresh(fm)
            return fm
        except SQLAlchemyError as e:
            await db.rollback()
            raise DatabaseError(f"Failed to save file metadata: {e}") from e

    async def get_file_metadata_by_file_id(
        self,
        db: AsyncSession,
        file_id: str,
    ) -> Optional[FileMetadata]:
        try:
            result = await db.execute(
                select(FileMetadata).filter(FileMetadata.file_id == file_id)
            )
            return result.scalars().first()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get file by ID {file_id}: {e}") from e

    async def get_file_metadata_by_stored_filename(
        self,
        db: AsyncSession,
        stored_filename: str,
    ) -> Optional[FileMetadata]:
        try:
            result = await db.execute(
                select(FileMetadata).filter(
                    FileMetadata.stored_filename == stored_filename
                )
            )
            return result.scalars().first()
        except SQLAlchemyError as e:
            raise DatabaseError(
                f"Failed to get file by stored name {stored_filename}: {e}"
            ) from e

    async def get_file_metadata_by_user_id(
        self,
        db: AsyncSession,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[FileMetadata]:
        try:
            result = await db.execute(
                select(FileMetadata)
                .filter(FileMetadata.user_id == user_id)
                .offset(skip)
                .limit(limit)
            )
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get files by user {user_id}: {e}") from e

    async def get_all_file_metadata(self, db: AsyncSession) -> List[FileMetadata]:
        try:
            result = await db.execute(select(FileMetadata))
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get all file metadata: {e}") from e

    async def get_file_metadata_by_userid_and_fileid(
        self,
        db: AsyncSession,
        user_id: str,
        file_id: str,
    ) -> Optional[FileMetadata]:
        try:
            result = await db.execute(
                select(FileMetadata).filter(
                    FileMetadata.user_id == user_id,
                    FileMetadata.file_id == file_id,
                )
            )
            return result.scalars().first()
        except SQLAlchemyError as e:
            raise DatabaseError(
                f"Failed to get file {file_id} for user {user_id}: {e}"
            ) from e

    async def delete_file_metadata(self, db: AsyncSession, file_id: str) -> int:
        try:
            result = await db.execute(
                delete(FileMetadata).filter(FileMetadata.file_id == file_id)
            )
            await db.commit()
            return result.rowcount
        except SQLAlchemyError as e:
            await db.rollback()
            raise DatabaseError(f"Failed to delete file metadata: {e}") from e

    async def save_chunks(
        self,
        db: AsyncSession,
        chunks: list,
        user_id: str,
        file_id: str,
        file_name: str,
    ) -> List[Chunk]:
        try:
            new_chunks = [
                Chunk(
                    user_id=user_id,
                    file_id=file_id,
                    file_name=file_name,
                    content=chunk["content"],
                    summary=chunk.get("summary", ""),
                    size=len(chunk["content"]),
                    name=chunk.get("heading", ""),
                )
                for chunk in chunks
            ]
            db.add_all(new_chunks)
            await db.commit()
            return new_chunks
        except SQLAlchemyError as e:
            await db.rollback()
            raise DatabaseError(f"Failed to save chunks: {e}") from e

    async def get_chunk_by_id(
        self,
        db: AsyncSession,
        chunk_id: int,
    ) -> Optional[Chunk]:
        try:
            result = await db.execute(select(Chunk).filter(Chunk.id == chunk_id))
            return result.scalars().first()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get chunk {chunk_id}: {e}") from e

    async def get_chunks_by_file_id(
        self,
        db: AsyncSession,
        file_id: str,
    ) -> List[Chunk]:
        try:
            result = await db.execute(select(Chunk).filter(Chunk.file_id == file_id))
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get chunks for file {file_id}: {e}") from e

    async def get_chunks_by_file_ids(
        self,
        db: AsyncSession,
        file_ids: list,
    ) -> List[Chunk]:
        try:
            result = await db.execute(select(Chunk).filter(Chunk.file_id.in_(file_ids)))
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get chunks for files {file_ids}: {e}") from e

    async def delete_chunk_by_id(self, db: AsyncSession, chunk_id: str) -> int:
        try:
            result = await db.execute(delete(Chunk).filter(Chunk.id == chunk_id))
            await db.commit()
            return result.rowcount
        except SQLAlchemyError as e:
            await db.rollback()
            raise DatabaseError(f"Failed to delete chunk {chunk_id}: {e}") from e

    async def delete_chunks_by_file_id(self, db: AsyncSession, file_id: str) -> int:
        try:
            result = await db.execute(delete(Chunk).filter(Chunk.file_id == file_id))
            await db.commit()
            return result.rowcount
        except SQLAlchemyError as e:
            await db.rollback()
            raise DatabaseError(f"Failed to delete chunks for file {file_id}: {e}") from e

    async def save_questions(
        self,
        db: AsyncSession,
        user_id: str,
        file_id: str,
        questions: list,
        chunk_id: str,
    ) -> int:
        try:
            new_questions = [
                Question(
                    user_id=user_id,
                    file_id=file_id,
                    chunk_id=chunk_id,
                    question=question["question"],
                    label=question.get("label", "uncategorized"),
                )
                for question in questions
            ]
            db.add_all(new_questions)
            await db.commit()
            return len(new_questions)
        except SQLAlchemyError as e:
            await db.rollback()
            raise DatabaseError(f"Failed to save questions: {e}") from e

    async def get_questions_by_chunk_id(
        self,
        db: AsyncSession,
        chunk_id: int,
    ) -> List[Question]:
        try:
            result = await db.execute(select(Question).filter(Question.chunk_id == chunk_id))
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get questions for chunk {chunk_id}: {e}") from e

    async def delete_questions_by_chunk_id(self, db: AsyncSession, chunk_id: str) -> int:
        try:
            result = await db.execute(delete(Question).filter(Question.chunk_id == chunk_id))
            await db.commit()
            return result.rowcount
        except SQLAlchemyError as e:
            await db.rollback()
            raise DatabaseError(
                f"Failed to delete questions for chunk {chunk_id}: {e}"
            ) from e
