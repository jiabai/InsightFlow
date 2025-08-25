"""
Database manager module for InsightFlow.

This module provides database models and operations for managing file metadata,
chunks and questions in the InsightFlow application. It handles database connections,
CRUD operations and error handling using SQLAlchemy ORM.

Models:
- FileMetadata: Stores metadata about uploaded files
- Chunk: Represents segments of processed files
- Question: Stores questions generated from file chunks

The DatabaseManager class provides methods to interact with these models
and manage database operations in an async context.
"""

import os
from typing import List, Optional
from datetime import datetime
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, select, delete
from sqlalchemy.orm import relationship
from sqlalchemy.exc import SQLAlchemyError

from be.common.exceptions import DatabaseError

Base = declarative_base()

class FileMetadata(Base):
    """
    Model class for storing file metadata information.

    This class represents the file_metadata table in the database and stores
    information about uploaded files including file ID, user ID, filename,
    file size, type and upload timestamps.

    Attributes:
        id (int): Primary key
        file_id (str): Unique identifier for the file
        user_id (str): ID of the user who uploaded the file
        filename (str): Original name of the uploaded file
        file_size (int): Size of the file in bytes
        file_type (str): MIME type or extension of the file
        upload_time (datetime): When the file was uploaded
        stored_filename (str): Name used to store the file in the system
    """
    __tablename__ = "file_metadata"

    id = Column(Integer, primary_key=True)
    file_id = Column(String(255), unique=True, index=True)
    user_id = Column(String(255))
    filename = Column(String(255))
    file_size = Column(Integer)
    file_type = Column(String(255))
    upload_time = Column(DateTime, default=datetime.now)
    stored_filename = Column(String(255))

class Chunk(Base):
    """
    Model class for storing file chunk information.

    This class represents the chunks table in the database and stores
    information about segments of processed files.

    Attributes:
        id (str): Primary key
        name (str): Name of the chunk
        project_id (str): ID of the project the chunk belongs to
        file_id (str): ID of the file the chunk is from
        file_name (str): Name of the file the chunk is from
        content (text): Content of the chunk
        summary (text): Summary of the chunk
        size (int): Size of the chunk in bytes
        created_at (datetime): When the chunk was created
        updated_at (datetime): When the chunk was last updated
    """
    __tablename__ = 'chunks'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(255))
    name = Column(String(255))
    file_id = Column(String(255), ForeignKey('file_metadata.file_id'), index=True)
    file_name = Column(String(255))
    content = Column(Text)
    summary = Column(Text)
    size = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    questions = relationship("Question", back_populates="chunk")

class Question(Base):
    """
    Model class for storing questions generated from file chunks.

    This class represents the questions table in the database and stores
    information about questions generated from processed file chunks.

    Attributes:
        id (str): Primary key
        file_id (str): ID of the file the question is from
        user_id (str): ID of the user who owns the question
        chunk_id (str): ID of the chunk the question is from
        question (text): The actual question text
        label (str): Category/label for the question
        answered (bool): Whether the question has been answered
        created_at (datetime): When the question was created
        updated_at (datetime): When the question was last updated
    """
    __tablename__ = 'questions'

    id = Column(Integer, primary_key=True)
    file_id = Column(String(255), ForeignKey('file_metadata.file_id'), index=True)
    user_id = Column(String(255))
    chunk_id = Column(Integer, ForeignKey('chunks.id'))
    question = Column(Text)
    label = Column(String(255))
    answered = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    chunk = relationship("Chunk", back_populates="questions")

class DatabaseManager:
    """
    Database manager class for InsightFlow.

    This class provides methods to interact with the database, including
    initializing the database, creating tables, and managing database sessions.

    Attributes:
        engine (AsyncEngine): SQLAlchemy async engine for database operations
        async_session (AsyncSession): SQLAlchemy async session factory
    """
    async def _create_all_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await self.engine.dispose()
        self._tables_created = True

    def __init__(self):
        self.database_name = os.getenv("DB_NAME", "insight_flow")
        self.database_url = (
            f"mysql+aiomysql://root:123456@192.168.31.233/"
            f"{self.database_name}?charset=utf8mb4"
        )
        self.engine = None
        self.async_session = None
        self._tables_created = False

    async def initialize(self):
        """
        Initialize the database engine and session factory.
        """
        if self.engine:
            return
        try:
            self.engine = create_async_engine(
                self.database_url,
                echo=False,
                pool_size=10,          # 连接池大小
                max_overflow=20,       # 最大溢出连接数
                pool_timeout=30,       # 获取连接超时时间
                pool_recycle=3600,     # 连接回收时间（1小时）
                pool_pre_ping=True     # 连接前ping检查
            )
            self.async_session = async_sessionmaker(
                self.engine,
                expire_on_commit=False,
                class_=AsyncSession
            )
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to initialize database: {e}") from e

    async def init_db(self):
        """
        Initialize the database by creating all tables.
        """
        if self._tables_created:
            return
        try:
            await self._create_all_tables()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to create database tables: {e}") from e

    async def dispose_engine(self):
        """
        Dispose the database engine.
        """
        if self.engine:
            await self.engine.dispose()

    @asynccontextmanager
    async def get_db(self):
        """
        Get a database session.

        This method provides a context manager for database sessions,
        ensuring that the session is properly closed after use.

        Yields:
            AsyncSession: A database session object.
        """
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
        stored_filename: str
    ) -> FileMetadata:
        """
        Save file metadata to the database.

        Args:
            db (AsyncSession): Database session object
            file_id (str): Unique identifier for the file
            user_id (str): Unique identifier for the user
            filename (str): Name of the file
            file_size (int): Size of the file in bytes
            file_type (str): Type of the file (e.g., 'pdf', 'docx')
            stored_filename (str): Name of the file as stored in the system

        Returns:
            FileMetadata: The saved file metadata object

        Raises:
            DatabaseError: If there's an error while saving the file metadata
        """
        try:
            file_metadata = FileMetadata(
                file_id=file_id,
                user_id=user_id,
                filename=filename,
                file_size=file_size,
                file_type=file_type,
                stored_filename=stored_filename
            )
            db.add(file_metadata)
            await db.commit()
            await db.refresh(file_metadata)
            return file_metadata
        except SQLAlchemyError as e:
            await db.rollback()
            raise DatabaseError(f"Failed to save file metadata: {e}") from e

    async def get_file_metadata_by_file_id(
        self,
        db: AsyncSession,
        file_id: str
    ) -> Optional[FileMetadata]:
        """
        Get file metadata by file ID.

        Args:
            db (AsyncSession): Database session object
            file_id (str): Unique identifier for the file

        Returns:
            Optional[FileMetadata]: File metadata object if found, None otherwise

        Raises:
            DatabaseError: If there's an error while querying the database
        """
        try:
            result = await db.execute(
                select(FileMetadata)
                .filter(FileMetadata.file_id == file_id)
            )
            return result.scalars().first()
        except SQLAlchemyError as e:
            raise DatabaseError(
                f"Failed to get file metadata by file ID {file_id}: {e}"
            ) from e

    async def get_file_metadata_by_stored_filename(
        self,
        db: AsyncSession,
        stored_filename: str
    ) -> Optional[FileMetadata]:
        """
        Get file metadata by stored filename.

        Args:
            db (AsyncSession): Database session object
            stored_filename (str): Name of the file as stored in the system

        Returns:
            Optional[FileMetadata]: File metadata object if found, None otherwise

        Raises:
            DatabaseError: If there's an error while querying the database
        """
        try:
            result = await db.execute(
                select(FileMetadata)
                .filter(FileMetadata.stored_filename == stored_filename)
            )
            return result.scalars().first()
        except SQLAlchemyError as e:
            raise DatabaseError(
                f"Failed to get file metadata by stored filename {stored_filename}: {e}"
            ) from e

    async def get_file_metadata_by_user_id(
        self,
        db: AsyncSession,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[FileMetadata]:
        """
        Get file metadata by user ID.

        Args:
            db (AsyncSession): Database session object
            user_id (str): Unique identifier for the user
            skip (int): Number of records to skip (default: 0)
            limit (int): Maximum number of records to return (default: 100)

        Returns:
            List[FileMetadata]: List of file metadata objects

        Raises:
            DatabaseError: If there's an error while querying the database
        """
        try:
            result = await db.execute(
                select(FileMetadata)
                .filter(FileMetadata.user_id == user_id)
                .offset(skip)
                .limit(limit)
            )
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get files by user ID {user_id}: {e}") from e

    async def get_all_file_metadata(
        self,
        db: AsyncSession
    ) -> List[FileMetadata]:
        """
        Get all file metadata from the database.

        Args:
            db (AsyncSession): Database session object

        Returns:
            List[FileMetadata]: List of all file metadata objects

        Raises:
            DatabaseError: If there's an error while querying the database
        """
        try:
            result = await db.execute(select(FileMetadata))
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get all file metadata: {e}") from e

    async def get_file_metadata_by_userid_and_fileid(
        self,
        db: AsyncSession,
        user_id: str,
        file_id: str
    ) -> Optional[FileMetadata]:
        """
        Get file metadata by user ID and file ID.

        Args:
            db (AsyncSession): Database session object
            user_id (str): Unique identifier for the user
            file_id (str): Unique identifier for the file

        Returns:
            Optional[FileMetadata]: File metadata object if found, None otherwise

        Raises:
            DatabaseError: If there's an error while querying the database
        """
        try:
            result = await db.execute(
                select(FileMetadata)
                .filter(FileMetadata.user_id == user_id)
                .filter(FileMetadata.file_id == file_id)
            )
            return result.scalars().first()
        except SQLAlchemyError as e:
            error_msg = f"Failed to get file by user ID {user_id} "
            error_msg += f"and file ID {file_id}: {e}"
            raise DatabaseError(error_msg) from e

    async def get_chunks_by_file_id(
        self,
        db: AsyncSession,
        file_id: str
    ) -> List[Chunk]:
        """
        Get chunks by file ID.

        Args:
            db (AsyncSession): Database session object
            file_id (str): Unique identifier for the file

        Returns:
            List[Chunk]: List of chunk objects

        Raises:
            DatabaseError: If there's an error while querying the database
        """
        try:
            result = await db.execute(select(Chunk).filter(Chunk.file_id == file_id))
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get chunk by file ID {file_id}: {e}") from e

    async def get_questions_by_chunk_id(
        self,
        db: AsyncSession,
        chunk_id: str
    ) -> List[Question]:
        """
        Get questions by chunk ID.

        Args:
            db (AsyncSession): Database session object
            chunk_id (str): Unique identifier for the chunk

        Returns:
            List[Question]: List of question objects

        Raises:
            DatabaseError: If there's an error while querying the database
        """
        try:
            query = select(Question).filter(Question.chunk_id == chunk_id)
            result = await db.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get questions by chunk ID {chunk_id}: {e}") from e

    async def delete_questions_by_chunk_id(
        self,
        db: AsyncSession,
        chunk_id: str
    ):
        """
        Delete questions by chunk ID.

        Args:
            db (AsyncSession): Database session object
            chunk_id (str): Unique identifier for the chunk

        Returns:
            int: Number of rows deleted

        Raises:
            DatabaseError: If there's an error while querying the database
        """
        try:
            result = await db.execute(delete(Question).filter(Question.chunk_id == chunk_id))
            await db.commit()
        except SQLAlchemyError as e:
            await db.rollback()
            raise DatabaseError(f"Failed to delete questions by chunk ID {chunk_id}: {e}") from e
        return result.rowcount

    async def save_questions(
        self,
        db: AsyncSession,
        user_id: str,
        file_id: str,
        questions: list,
        chunk_id: str
    ) -> int:
        """
        Save questions to the database.

        Args:
            db (AsyncSession): Database session object
            project_id (str): Unique identifier for the project
            questions (list): List of question data dictionaries
            chunk_id (str): Unique identifier for the chunk

        Returns:
            int: Number of rows inserted

        Raises:
            DatabaseError: If there's an error while querying the database
        """
        try:
            new_questions = []
            for q_data in questions:
                new_question = Question(
                    user_id=user_id,
                    file_id=file_id,
                    chunk_id=chunk_id,
                    question=q_data['question'],
                    label=q_data.get('label', 'uncategorized')
                )
                new_questions.append(new_question)

            db.add_all(new_questions)
            await db.commit()
            return len(new_questions)
        except SQLAlchemyError as e:
            await db.rollback()
            raise DatabaseError(f"Failed to save questions: {e}") from e

    async def save_chunks(
        self,
        db: AsyncSession,
        chunks: list,
        user_id: str,
        file_id: str,
        file_name: str
    ) -> List[Chunk]:
        """
        Save chunks to the database.

        Args:
            db (AsyncSession): Database session object
            chunks (list): List of chunk data dictionaries
            project_id (str): Unique identifier for the project
            file_id (str): Unique identifier for the file
            file_name (str): Name of the file

        Returns:
            List[Chunk]: List of chunk objects

        Raises:
            DatabaseError: If there's an error while querying the database
        """
        try:
            new_chunks = []
            for chunk_data in chunks:
                new_chunk = Chunk(
                    user_id=user_id,
                    file_id=file_id,
                    file_name=file_name,
                    content=chunk_data['content'],
                    summary=chunk_data.get('summary', ''),
                    size=len(chunk_data['content']),
                    name=chunk_data.get('heading', '')
                )
                new_chunks.append(new_chunk)

            db.add_all(new_chunks)
            await db.commit()
            return new_chunks
        except SQLAlchemyError as e:
            await db.rollback()
            raise DatabaseError(f"Failed to save chunks: {e}") from e

    async def delete_file_metadata(self, db: AsyncSession, file_id: str) -> int:
        """
        Delete file metadata by file ID.

        Args:
            db (AsyncSession): Database session object
            file_id (str): Unique identifier for the file

        Returns:
            int: Number of rows deleted

        Raises:
            DatabaseError: If there's an error while querying the database
        """
        try:
            result = await db.execute(delete(FileMetadata).filter(FileMetadata.file_id == file_id))
            await db.commit()
            return result.rowcount
        except SQLAlchemyError as e:
            await db.rollback()
            raise DatabaseError(f"Failed to delete file metadata: {e}") from e

    async def get_chunk_by_id(self, db: AsyncSession, chunk_id: str) -> Chunk:
        """
        Get chunk by chunk ID.

        Args:
            db (AsyncSession): Database session object
            chunk_id (str): Unique identifier for the chunk

        Returns:
            Chunk: Chunk object

        Raises:
            DatabaseError: If there's an error while querying the database
        """
        try:
            result = await db.execute(select(Chunk).filter(Chunk.id == chunk_id))
            return result.scalars().first()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get chunk by ID {chunk_id}: {e}") from e

    async def get_chunks_by_file_ids(self, db: AsyncSession, file_ids: list) -> List[Chunk]:
        """
        Get chunks by file IDs.

        Args:
            db (AsyncSession): Database session object
            file_ids (list): List of file ID strings

        Returns:
            list[Chunk]: List of chunk objects

        Raises:
            DatabaseError: If there's an error while querying the database
        """
        try:
            result = await db.execute(select(Chunk).filter(Chunk.file_id.in_(file_ids)))
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get chunks by file IDs {file_ids}: {e}") from e

    async def delete_chunk_by_id(self, db: AsyncSession, chunk_id: str) -> int:
        """
        Delete chunk by chunk ID.

        Args:
            db (AsyncSession): Database session object
            chunk_id (str): Unique identifier for the chunk

        Returns:
            int: Number of rows deleted

        Raises:
            DatabaseError: If there's an error while querying the database
        """
        try:
            result = await db.execute(delete(Chunk).filter(Chunk.id == chunk_id))
            await db.commit()
            return result.rowcount
        except SQLAlchemyError as e:
            await db.rollback()
            raise DatabaseError(f"Failed to delete chunk by ID {chunk_id}: {e}") from e

    async def delete_chunks_by_file_id(self, db: AsyncSession, file_id: str) -> int:
        """
        Delete chunks by file ID.

        Args:
            db (AsyncSession): Database session object
            file_id (str): Unique identifier for the file

        Returns:
            int: Number of rows deleted

        Raises:
            DatabaseError: If there's an error while querying the database
        """
        try:
            result = await db.execute(delete(Chunk).filter(Chunk.file_id == file_id))
            await db.commit()
            return result.rowcount
        except SQLAlchemyError as e:
            await db.rollback()
            raise DatabaseError(f"Failed to delete chunks by file ID {file_id}: {e}") from e
