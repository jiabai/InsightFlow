"""
InsightRepository — abstract repository interface.

Defines the single seam through which all data access flows.
Two adapters: InsightMySQLRepository (production) and InsightMemoryRepository (tests).
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from server.common.models import FileMetadata, Chunk, Question


class InsightRepository(ABC):
    """Abstract repository for InsightFlow data access.

    All 22 CRUD methods grouped by entity. Each adapter implements the
    full set behind a single interface.
    """

    # ── Lifecycle ──────────────────────────────────────────────

    @abstractmethod
    async def initialize(self) -> None: ...

    @abstractmethod
    async def init_db(self) -> None: ...

    @abstractmethod
    async def dispose_engine(self) -> None: ...

    @abstractmethod
    def get_db(self): ...

    # ── File metadata ──────────────────────────────────────────

    @abstractmethod
    async def save_file_metadata(
        self, db: AsyncSession, file_id: str, user_id: str,
        filename: str, file_size: int, file_type: str, stored_filename: str,
    ) -> FileMetadata: ...

    @abstractmethod
    async def get_file_metadata_by_file_id(
        self, db: AsyncSession, file_id: str,
    ) -> Optional[FileMetadata]: ...

    @abstractmethod
    async def get_file_metadata_by_stored_filename(
        self, db: AsyncSession, stored_filename: str,
    ) -> Optional[FileMetadata]: ...

    @abstractmethod
    async def get_file_metadata_by_user_id(
        self, db: AsyncSession, user_id: str, skip: int = 0, limit: int = 100,
    ) -> List[FileMetadata]: ...

    @abstractmethod
    async def get_all_file_metadata(
        self, db: AsyncSession,
    ) -> List[FileMetadata]: ...

    @abstractmethod
    async def get_file_metadata_by_userid_and_fileid(
        self, db: AsyncSession, user_id: str, file_id: str,
    ) -> Optional[FileMetadata]: ...

    @abstractmethod
    async def delete_file_metadata(
        self, db: AsyncSession, file_id: str,
    ) -> int: ...

    # ── Chunks ──────────────────────────────────────────────────

    @abstractmethod
    async def save_chunks(
        self, db: AsyncSession, chunks: list, user_id: str,
        file_id: str, file_name: str,
    ) -> List[Chunk]: ...

    @abstractmethod
    async def get_chunk_by_id(
        self, db: AsyncSession, chunk_id: int,
    ) -> Optional[Chunk]: ...

    @abstractmethod
    async def get_chunks_by_file_id(
        self, db: AsyncSession, file_id: str,
    ) -> List[Chunk]: ...

    @abstractmethod
    async def get_chunks_by_file_ids(
        self, db: AsyncSession, file_ids: list,
    ) -> List[Chunk]: ...

    @abstractmethod
    async def delete_chunk_by_id(
        self, db: AsyncSession, chunk_id: str,
    ) -> int: ...

    @abstractmethod
    async def delete_chunks_by_file_id(
        self, db: AsyncSession, file_id: str,
    ) -> int: ...

    # ── Questions ───────────────────────────────────────────────

    @abstractmethod
    async def save_questions(
        self, db: AsyncSession, user_id: str, file_id: str,
        questions: list, chunk_id: str,
    ) -> int: ...

    @abstractmethod
    async def get_questions_by_chunk_id(
        self, db: AsyncSession, chunk_id: int,
    ) -> List[Question]: ...

    @abstractmethod
    async def delete_questions_by_chunk_id(
        self, db: AsyncSession, chunk_id: str,
    ) -> int: ...
