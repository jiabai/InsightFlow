"""
InsightMemoryRepository — in-memory adapter of InsightRepository for testing.

All data is held in dicts/lists within a single instance.
No I/O, deterministic, ideal for unit tests.
"""

from typing import Optional, List
from contextlib import asynccontextmanager
from unittest.mock import MagicMock

from be.common.models import FileMetadata, Chunk, Question
from be.common.repository import InsightRepository


class InsightMemoryRepository(InsightRepository):
    """In-memory repository with no external dependencies.

    Thread-safe by design (single-threaded test usage). Not suitable for
    production use — data is lost when the instance is destroyed.
    """

    def __init__(self) -> None:
        self._files: List[FileMetadata] = []
        self._chunks: List[Chunk] = []
        self._questions: List[Question] = []
        self._next_file_id = 1
        self._next_chunk_id = 1
        self._next_question_id = 1

    # ── Lifecycle — no-op ───────────────────────────────────────

    async def initialize(self) -> None:
        pass

    async def init_db(self) -> None:
        pass

    async def dispose_engine(self) -> None:
        pass

    @asynccontextmanager
    async def get_db(self):
        """Yield a MagicMock that satisfies the AsyncSession protocol in tests."""
        yield MagicMock()

    # ── Helpers ─────────────────────────────────────────────────

    def _make_file_meta(self, file_id: str, user_id: str, filename: str,
                         file_size: int, file_type: str, stored_filename: str) -> FileMetadata:
        fm = FileMetadata()
        fm.id = self._next_file_id
        self._next_file_id += 1
        fm.file_id = file_id
        fm.user_id = user_id
        fm.filename = filename
        fm.file_size = file_size
        fm.file_type = file_type
        fm.stored_filename = stored_filename
        return fm

    def _make_chunk(self, content: str, user_id: str, file_id: str,
                     file_name: str, summary: str, heading: str) -> Chunk:
        c = Chunk()
        c.id = self._next_chunk_id
        self._next_chunk_id += 1
        c.user_id = user_id
        c.file_id = file_id
        c.file_name = file_name
        c.content = content
        c.summary = summary
        c.name = heading
        c.size = len(content)
        return c

    def _make_question(self, user_id: str, file_id: str, chunk_id: str,
                        question: str, label: str) -> Question:
        q = Question()
        q.id = self._next_question_id
        self._next_question_id += 1
        q.user_id = user_id
        q.file_id = file_id
        q.chunk_id = chunk_id
        q.question = question
        q.label = label
        return q

    # ── File metadata ──────────────────────────────────────────

    async def save_file_metadata(
        self, db, file_id: str, user_id: str, filename: str,
        file_size: int, file_type: str, stored_filename: str,
    ) -> FileMetadata:
        fm = self._make_file_meta(file_id, user_id, filename, file_size, file_type, stored_filename)
        self._files.append(fm)
        return fm

    async def get_file_metadata_by_file_id(self, db, file_id: str) -> Optional[FileMetadata]:
        for f in self._files:
            if f.file_id == file_id:
                return f
        return None

    async def get_file_metadata_by_stored_filename(self, db, stored_filename: str) -> Optional[FileMetadata]:
        for f in self._files:
            if f.stored_filename == stored_filename:
                return f
        return None

    async def get_file_metadata_by_user_id(self, db, user_id: str, skip: int = 0, limit: int = 100) -> List[FileMetadata]:
        return [f for f in self._files if f.user_id == user_id][skip:skip + limit]

    async def get_all_file_metadata(self, db) -> List[FileMetadata]:
        return list(self._files)

    async def get_file_metadata_by_userid_and_fileid(self, db, user_id: str, file_id: str) -> Optional[FileMetadata]:
        for f in self._files:
            if f.user_id == user_id and f.file_id == file_id:
                return f
        return None

    async def delete_file_metadata(self, db, file_id: str) -> int:
        before = len(self._files)
        self._files = [f for f in self._files if f.file_id != file_id]
        return before - len(self._files)

    # ── Chunks ──────────────────────────────────────────────────

    async def save_chunks(self, db, chunks: list, user_id: str, file_id: str, file_name: str) -> List[Chunk]:
        new = []
        for c in chunks:
            ch = self._make_chunk(c["content"], user_id, file_id, file_name,
                                   c.get("summary", ""), c.get("heading", ""))
            self._chunks.append(ch)
            new.append(ch)
        return new

    async def get_chunk_by_id(self, db, chunk_id: int) -> Optional[Chunk]:
        for c in self._chunks:
            if c.id == chunk_id:
                return c
        return None

    async def get_chunks_by_file_id(self, db, file_id: str) -> List[Chunk]:
        return [c for c in self._chunks if c.file_id == file_id]

    async def get_chunks_by_file_ids(self, db, file_ids: list) -> List[Chunk]:
        return [c for c in self._chunks if c.file_id in file_ids]

    async def delete_chunk_by_id(self, db, chunk_id: str) -> int:
        before = len(self._chunks)
        self._chunks = [c for c in self._chunks if c.id != chunk_id]
        return before - len(self._chunks)

    async def delete_chunks_by_file_id(self, db, file_id: str) -> int:
        before = len(self._chunks)
        self._chunks = [c for c in self._chunks if c.file_id != file_id]
        return before - len(self._chunks)

    # ── Questions ───────────────────────────────────────────────

    async def save_questions(self, db, user_id: str, file_id: str,
                              questions: list, chunk_id: str) -> int:
        count = 0
        for q in questions:
            qo = self._make_question(user_id, file_id, chunk_id,
                                      q["question"], q.get("label", "uncategorized"))
            self._questions.append(qo)
            count += 1
        return count

    async def get_questions_by_chunk_id(self, db, chunk_id: int) -> List[Question]:
        return [q for q in self._questions if q.chunk_id == chunk_id]

    async def delete_questions_by_chunk_id(self, db, chunk_id: str) -> int:
        before = len(self._questions)
        self._questions = [q for q in self._questions if q.chunk_id != chunk_id]
        return before - len(self._questions)
