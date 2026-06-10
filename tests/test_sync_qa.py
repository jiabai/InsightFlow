"""
Test: Sync Q&A (#06) — POST /llm/query endpoint.
"""
import pytest


class TestSyncQA:
    """Verify synchronous LLM query endpoint."""

    async def _seed_question(self, memory_repo):
        """Seed a chunk and question into the mock repository."""
        from be.common.models import FileMetadata, Chunk, Question

        async with memory_repo.get_db() as db:
            # Create file metadata
            await memory_repo.save_file_metadata(
                db, file_id="qa-test-file",
                user_id="user123", filename="test.md",
                file_size=100, file_type="markdown",
                stored_filename="stored.md",
            )
            # Create a chunk
            await memory_repo.save_chunks(
                db, [{"summary": "Test Chunk", "content": "This is the chunk content for context."}],
                user_id="user123", file_id="qa-test-file", file_name="test.md",
            )
            # Get the chunk we just saved
            chunks = await memory_repo.get_chunks_by_file_id(db, "qa-test-file")
            chunk = chunks[0]
            # Create a question
            await memory_repo.save_questions(
                db, user_id="user123", file_id="qa-test-file",
                questions=[{
                    "question": "What is this about?",
                    "label": "General",
                    "chunk_id": chunk.id,
                }],
                chunk_id=chunk.id,
            )
            # Get the question we just saved
            questions = await memory_repo.get_questions_by_chunk_id(db, chunk.id)
            return chunk, questions[0]

    async def test_query_with_valid_ids_returns_answer(self, client, memory_repo):
        """Valid question_id + chunk_id should return an answer."""
        chunk, question = await self._seed_question(memory_repo)

        response = client.post("/llm/query", json={
            "question_id": question.id,
            "chunk_id": chunk.id,
        })
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data
        assert len(data["choices"]) > 0
        content = data["choices"][0]["message"]["content"]
        assert len(content) > 0, "Answer should not be empty"

    async def test_query_nonexistent_question(self, client):
        """Non-existent question_id should return an error."""
        response = client.post("/llm/query", json={
            "question_id": 99999,
            "chunk_id": 99999,
        })
        assert response.status_code in {400, 404, 500}

    async def test_empty_request_rejected(self, client):
        """Empty JSON body should be rejected."""
        response = client.post("/llm/query", json={})
        assert response.status_code in {400, 422}

    async def test_missing_fields_rejected(self, client):
        """Missing required fields should be rejected."""
        response = client.post("/llm/query", json={"question_id": 1})
        assert response.status_code in {400, 422}
