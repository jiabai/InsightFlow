import os
import uuid
from typing import List
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
    数据库中文件元数据表的模型。
    """
    __tablename__ = "file_metadata"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(String(255), unique=True, index=True)
    user_id = Column(String(255), index=True)
    filename = Column(String(255), index=True)
    file_size = Column(Integer)
    file_type = Column(String(255))
    upload_time = Column(DateTime, default=datetime.now)
    stored_filename = Column(String(255), unique=True, index=True)

class Chunk(Base):
    __tablename__ = 'chunks'

    id = Column(String(255), primary_key=True)
    name = Column(String(255))
    project_id = Column(String(255), index=True)
    file_id = Column(String(255), ForeignKey('file_metadata.file_id'))
    file_name = Column(String(255))
    content = Column(Text)
    summary = Column(Text)
    size = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    questions = relationship("Question", back_populates="chunk")

class Question(Base):
    __tablename__ = 'questions'

    id = Column(String(255), primary_key=True)
    project_id = Column(String(255), index=True)
    chunk_id = Column(String(255), ForeignKey('chunks.id'))
    question = Column(Text)
    label = Column(String(255))
    answered = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    chunk = relationship("Chunk", back_populates="questions")

class DatabaseManager:
    """
    数据库操作封装类
    """
    async def _create_all_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await self.engine.dispose()

    def __init__(self):
        # 数据库配置
        self.database_name = os.getenv("DB_NAME", "insight_flow")
        self.database_url = (
            f"mysql+aiomysql://root:123456@192.168.31.233/"
            f"{self.database_name}?charset=utf8mb4"
        )
        self.engine = None
        self.async_session = None

    async def initialize(self):
        try:
            self.engine = create_async_engine(self.database_url, echo=False)
            self.async_session = async_sessionmaker(
                self.engine,
                expire_on_commit=False,
                class_=AsyncSession
            )
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to initialize database: {e}") from e

    async def init_db(self):
        """
        初始化数据库，创建所有表。
        """
        try:
            await self._create_all_tables()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to initialize database tables: {e}") from e

    async def dispose_engine(self):
        if self.engine:
            await self.engine.dispose()

    @asynccontextmanager
    async def get_db(self):
        """
        获取数据库会话
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
    ):
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
    ) -> FileMetadata:
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
    ):
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
    ) -> FileMetadata:
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

    async def get_chunks_by_file_id(self, db: AsyncSession, file_id: str) -> List[Chunk]:
        try:
            result = await db.execute(select(Chunk).filter(Chunk.file_id == file_id))
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get chunk by file ID {file_id}: {e}") from e

    async def get_questions_by_chunk_id(self, db: AsyncSession, chunk_id: str):
        try:
            query = select(Question).filter(Question.chunk_id == chunk_id)
            result = await db.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get questions by chunk ID {chunk_id}: {e}") from e

    async def get_questions_by_project_id(self, db: AsyncSession, project_id: str):
        try:
            result = await db.execute(select(Question).filter(Question.project_id == project_id))
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get questions by project ID {project_id}: {e}") from e

    async def delete_questions_by_chunk_id(self, db: AsyncSession, chunk_id: str):
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
        project_id: str,
        questions: list,
        chunk_id: str
    ):
        """
        保存问题到数据库
        """
        try:
            # # 首先删除已存在的问题
            # await db.execute(
            #     delete(Question)
            #     .where(Question.project_id == project_id, Question.chunk_id == chunk_id)
            # )

            # 然后插入新的问题
            new_questions = []
            for q_data in questions:
                new_question = Question(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
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
        project_id: str,
        file_id: str,
        file_name: str
    ):
        try:
            # 然后插入新的块
            new_chunks = []
            for chunk_data in chunks:
                new_chunk = Chunk(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
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

    async def delete_file_metadata(self, db: AsyncSession, file_id: str):
        try:
            result = await db.execute(delete(FileMetadata).filter(FileMetadata.file_id == file_id))
            await db.commit()
            return result.rowcount
        except SQLAlchemyError as e:
            await db.rollback()
            raise DatabaseError(f"Failed to delete file metadata: {e}") from e

    async def get_chunk_by_id(self, db: AsyncSession, chunk_id: str):
        try:
            result = await db.execute(select(Chunk).filter(Chunk.id == chunk_id))
            return result.scalars().first()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get chunk by ID {chunk_id}: {e}") from e

    async def get_chunks_by_file_ids(self, db: AsyncSession, file_ids: list) -> list[Chunk]:
        try:
            result = await db.execute(select(Chunk).filter(Chunk.file_id.in_(file_ids)))
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get chunks by file IDs {file_ids}: {e}") from e

    async def delete_chunk_by_id(self, db: AsyncSession, chunk_id: str):
        try:
            result = await db.execute(delete(Chunk).filter(Chunk.id == chunk_id))
            await db.commit()
            return result.rowcount
        except SQLAlchemyError as e:
            await db.rollback()
            raise DatabaseError(f"Failed to delete chunk by ID {chunk_id}: {e}") from e

    async def delete_chunks_by_file_id(self, db: AsyncSession, file_id: str):
        try:
            result = await db.execute(delete(Chunk).filter(Chunk.file_id == file_id))
            await db.commit()
            return result.rowcount
        except SQLAlchemyError as e:
            await db.rollback()
            raise DatabaseError(f"Failed to delete chunks by file ID {file_id}: {e}") from e
