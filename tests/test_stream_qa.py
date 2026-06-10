"""
Test: Stream Q&A (#08) — POST /llm/query/stream endpoint.
"""
import pytest


class TestStreamQA:
    """Verify streaming LLM query endpoint."""

    async def _seed_question(self, memory_repo):
        """Seed a chunk and question into the mock repository."""
        async with memory_repo.get_db() as db:
            await memory_repo.save_file_metadata(
                db, file_id="stream-test",
                user_id="user123", filename="test.md",
                file_size=100, file_type="markdown",
                stored_filename="stored.md",
            )
            await memory_repo.save_chunks(
                db, [{"summary": "Test", "content": "Chunk content for streaming."}],
                user_id="user123", file_id="stream-test", file_name="test.md",
            )
            chunks = await memory_repo.get_chunks_by_file_id(db, "stream-test")
            chunk = chunks[0]
            await memory_repo.save_questions(
                db, user_id="user123", file_id="stream-test",
                questions=[{"question": "Test Q?", "label": "General", "chunk_id": chunk.id}],
                chunk_id=chunk.id,
            )
            questions = await memory_repo.get_questions_by_chunk_id(db, chunk.id)
            return chunk, questions[0]

    async def test_stream_returns_sse(self, client, memory_repo):
        """Streaming endpoint should return SSE content type."""
        chunk, question = await self._seed_question(memory_repo)

        response = client.post("/llm/query/stream", json={
            "question_id": question.id,
            "chunk_id": chunk.id,
        })
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    async def test_stream_has_data_marker(self, client, memory_repo):
        """SSE stream should contain 'data:' markers."""
        chunk, question = await self._seed_question(memory_repo)

        response = client.post("/llm/query/stream", json={
            "question_id": question.id,
            "chunk_id": chunk.id,
        })
        content = response.text
        assert "data:" in content, "SSE stream should contain data: markers"

    async def test_stream_has_done_marker(self, client, memory_repo):
        """SSE stream should end with [DONE] marker."""
        chunk, question = await self._seed_question(memory_repo)

        response = client.post("/llm/query/stream", json={
            "question_id": question.id,
            "chunk_id": chunk.id,
        })
        assert "[DONE]" in response.text, "Stream should end with [DONE]"
