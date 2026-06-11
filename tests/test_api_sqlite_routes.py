import asyncio
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.api_services.insight_logger import setup_logging
from server.common.file_status_store import FileStatusStore
from server.common.insight_sqlite_repository import InsightSQLiteRepository
from server.common.local_storage import LocalStorage
from server.llm_knowledge_processing.llm_gateway import LLMGateway


@pytest.fixture
def sqlite_api_client(tmp_path, monkeypatch):
    monkeypatch.setenv("SQLITE_DB_PATH", str(tmp_path / "insight_flow.sqlite3"))
    repo = InsightSQLiteRepository()
    status_store = FileStatusStore(base_dir=tmp_path / "status_store")
    storage = LocalStorage(base_dir=str(tmp_path / "upload_file"))
    llm_gateway = LLMGateway(mock=True, mock_response="SQLite route mock answer.")

    async def setup_resources():
        await repo.initialize()
        await repo.init_db()
        await status_store.initialize()

    asyncio.run(setup_resources())

    app = FastAPI()
    setup_logging(app, log_file=f"test_api_sqlite_routes_{uuid4().hex}.log")

    from server.api_services.file_routes import (
        get_database_manager as file_get_db_mgr,
        get_db as file_get_db,
        get_status_store as file_get_status_store,
        get_storage_manager as file_get_storage,
        router as file_router,
    )
    from server.api_services.question_routes import (
        get_database_manager as question_get_db_mgr,
        get_db as question_get_db,
        get_llm_gateway as question_get_llm,
        get_status_store as question_get_status_store,
        get_storage_manager as question_get_storage,
        router as question_router,
    )
    from server.api_services.llm_routes import (
        get_database_manager as llm_get_db_mgr,
        get_db as llm_get_db,
        get_llm_gateway as llm_get_llm,
        get_status_store as llm_get_status_store,
        get_storage_manager as llm_get_storage,
        router as llm_router,
    )

    async def override_get_db():
        async with repo.get_db() as db:
            yield db

    app.include_router(file_router)
    app.include_router(question_router)
    app.include_router(llm_router)
    app.dependency_overrides.update({
        file_get_db_mgr: lambda: repo,
        file_get_db: override_get_db,
        file_get_status_store: lambda: status_store,
        file_get_storage: lambda: storage,
        question_get_db_mgr: lambda: repo,
        question_get_db: override_get_db,
        question_get_status_store: lambda: status_store,
        question_get_storage: lambda: storage,
        question_get_llm: lambda: llm_gateway,
        llm_get_db_mgr: lambda: repo,
        llm_get_db: override_get_db,
        llm_get_status_store: lambda: status_store,
        llm_get_storage: lambda: storage,
        llm_get_llm: lambda: llm_gateway,
    })

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client, repo, status_store
    finally:
        asyncio.run(repo.dispose_engine())


def test_upload_and_file_listing_use_sqlite_sessions(sqlite_api_client):
    client, _, _ = sqlite_api_client

    upload = client.post(
        "/upload/sqlite-user",
        files={"file": ("sqlite-smoke.md", b"# SQLite smoke\n\nContent.", "text/markdown")},
    )

    assert upload.status_code == 200, upload.text
    file_id = upload.json()["file_id"]
    assert upload.json()["status"] == "Upload Completed"

    status = client.get(f"/file_status/{file_id}")
    assert status.status_code == 200, status.text
    assert status.json()["status"] == "Pending"

    files = client.get("/files/")
    assert files.status_code == 200, files.text
    assert files.json()[0]["file_id"] == file_id


def test_config_manager_uses_runtime_storage_directories(tmp_path, monkeypatch):
    upload_dir = tmp_path / "upload_file"
    completed_dir = tmp_path / "completed"
    monkeypatch.setenv("LOCAL_STORAGE_BASE_DIR", str(upload_dir))
    monkeypatch.setenv("LOCAL_COMPLETED_DIR", str(completed_dir))

    from server.llm_knowledge_processing.config_manager import ConfigManager

    config = ConfigManager()

    assert config.upload_dir == str(upload_dir)
    assert config.completed_dir == str(completed_dir)
    assert upload_dir.exists()
    assert completed_dir.exists()


def test_llm_query_and_stream_use_sqlite_sessions(sqlite_api_client):
    client, repo, status_store = sqlite_api_client

    async def seed_question():
        async with repo.get_db() as db:
            await repo.save_file_metadata(
                db,
                file_id="llm-file",
                user_id="sqlite-user",
                filename="llm.md",
                file_size=128,
                file_type="text/markdown",
                stored_filename="sqlite-user_llm-file_llm.md",
            )
            chunks = await repo.save_chunks(
                db,
                [{"summary": "LLM chunk", "content": "The answer should use this context."}],
                user_id="sqlite-user",
                file_id="llm-file",
                file_name="llm.md",
            )
            await repo.save_questions(
                db,
                user_id="sqlite-user",
                file_id="llm-file",
                questions=[{"question": "What should the answer use?", "label": "General"}],
                chunk_id=chunks[0].id,
            )
            questions = await repo.get_questions_by_chunk_id(db, chunks[0].id)
            return chunks[0].id, questions[0].id

    chunk_id, question_id = asyncio.run(seed_question())
    asyncio.run(status_store.set_file_status("llm-file", "Completed"))

    response = client.post(
        "/llm/query",
        json={"question_id": question_id, "chunk_id": chunk_id},
    )
    assert response.status_code == 200, response.text
    assert response.json()["choices"][0]["message"]["content"] == "SQLite route mock answer."

    stream = client.post(
        "/llm/query/stream",
        json={"question_id": question_id, "chunk_id": chunk_id},
    )
    assert stream.status_code == 200, stream.text
    assert "text/event-stream" in stream.headers["content-type"]
    assert "data:" in stream.text

    questions = client.get("/questions/llm-file")
    assert questions.status_code == 200, questions.text
    assert questions.json()["questions"][0]["question_id"] == question_id
