"""
Test 2: InsightMemoryRepository CRUD — verifies the in-memory repository
can save, query, and delete file metadata correctly.
"""
import pytest


class TestInsightMemoryRepository:
    """Verify that InsightMemoryRepository implements all CRUD operations."""

    async def test_save_and_retrieve_file(self, memory_repo):
        """Save a file and fetch it back by file_id."""
        async with memory_repo.get_db() as db:
            file_id = "abc123"
            await memory_repo.save_file_metadata(
                db,
                file_id=file_id,
                user_id="user1",
                filename="test.md",
                file_size=1024,
                file_type="markdown",
                stored_filename="stored_test.md",
            )
            result = await memory_repo.get_file_metadata_by_file_id(db, file_id)
            assert result is not None
            assert result.file_id == file_id
            assert result.user_id == "user1"
            assert result.filename == "test.md"

    async def test_get_nonexistent_file_returns_none(self, memory_repo):
        """Querying a non-existent file should return None."""
        async with memory_repo.get_db() as db:
            result = await memory_repo.get_file_metadata_by_file_id(db, "nonexistent")
            assert result is None

    async def test_delete_file(self, memory_repo):
        """Delete a file and verify it's gone."""
        async with memory_repo.get_db() as db:
            file_id = "to-delete"
            await memory_repo.save_file_metadata(
                db,
                file_id=file_id,
                user_id="user1",
                filename="temp.md",
                file_size=100,
                file_type="markdown",
                stored_filename="temp_stored.md",
            )
            await memory_repo.delete_file_metadata(db, file_id)
            result = await memory_repo.get_file_metadata_by_file_id(db, file_id)
            assert result is None

    async def test_list_files_by_user(self, memory_repo):
        """List files belonging to a specific user."""
        async with memory_repo.get_db() as db:
            for i in range(3):
                await memory_repo.save_file_metadata(
                    db,
                    file_id=f"file-{i}",
                    user_id="user1",
                    filename=f"file-{i}.md",
                    file_size=100,
                    file_type="markdown",
                    stored_filename=f"stored-{i}.md",
                )
            results = await memory_repo.get_file_metadata_by_user_id(db, "user1")
            assert len(results) == 3

    async def test_multiple_users_isolated(self, memory_repo):
        """Files from different users should be isolated."""
        async with memory_repo.get_db() as db:
            await memory_repo.save_file_metadata(
                db, file_id="f1", user_id="alice",
                filename="a.md", file_size=100, file_type="md",
                stored_filename="a_stored.md",
            )
            await memory_repo.save_file_metadata(
                db, file_id="f2", user_id="bob",
                filename="b.md", file_size=200, file_type="md",
                stored_filename="b_stored.md",
            )
            alice_files = await memory_repo.get_file_metadata_by_user_id(db, "alice")
            bob_files = await memory_repo.get_file_metadata_by_user_id(db, "bob")
            assert len(alice_files) == 1
            assert len(bob_files) == 1
            assert alice_files[0].file_id == "f1"
            assert bob_files[0].file_id == "f2"
