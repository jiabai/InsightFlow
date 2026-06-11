import pytest
from sqlalchemy import text

from server.common.insight_sqlite_repository import InsightSQLiteRepository


@pytest.mark.asyncio
async def test_sqlite_repository_creates_database_and_persists_core_entities(
    tmp_path,
    monkeypatch,
):
    db_path = tmp_path / "nested" / "insight_flow.sqlite3"
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_path))

    repo = InsightSQLiteRepository()
    await repo.initialize()
    await repo.init_db()

    try:
        assert db_path.exists()

        async with repo.get_db() as db:
            table_rows = await db.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type = 'table' ORDER BY name"
                )
            )
            tables = {row[0] for row in table_rows}
            assert {"file_metadata", "chunks", "questions"}.issubset(tables)

            file_id = "file-1"
            await repo.save_file_metadata(
                db,
                file_id=file_id,
                user_id="user-1",
                filename="article.md",
                file_size=2048,
                file_type="markdown",
                stored_filename="user-1_file-1_article.md",
            )

            file_metadata = await repo.get_file_metadata_by_file_id(db, file_id)
            assert file_metadata is not None
            assert file_metadata.filename == "article.md"

            chunks = await repo.save_chunks(
                db,
                [
                    {"content": "First chunk", "summary": "First", "heading": "Intro"},
                    {"content": "Second chunk", "summary": "Second", "heading": "Body"},
                ],
                user_id="user-1",
                file_id=file_id,
                file_name="article.md",
            )
            assert len(chunks) == 2

            persisted_chunks = await repo.get_chunks_by_file_id(db, file_id)
            assert [chunk.name for chunk in persisted_chunks] == ["Intro", "Body"]

            saved_count = await repo.save_questions(
                db,
                user_id="user-1",
                file_id=file_id,
                questions=[
                    {"question": "What is the intro?", "label": "recall"},
                    {"question": "What is the body?", "label": "recall"},
                ],
                chunk_id=chunks[0].id,
            )
            assert saved_count == 2

            questions = await repo.get_questions_by_chunk_id(db, chunks[0].id)
            assert [question.question for question in questions] == [
                "What is the intro?",
                "What is the body?",
            ]

            assert await repo.delete_questions_by_chunk_id(db, chunks[0].id) == 2
            assert await repo.delete_chunks_by_file_id(db, file_id) == 2
            assert await repo.delete_file_metadata(db, file_id) == 1
    finally:
        await repo.dispose_engine()
