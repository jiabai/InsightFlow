import json

import pytest

from server.common.file_status_store import LocalFileStatusStore
from server.common.redis_manager import RedisManager


@pytest.mark.asyncio
async def test_file_status_store_persists_status_to_local_file(tmp_path):
    store = LocalFileStatusStore(base_dir=tmp_path)

    await store.initialize()
    await store.set_file_status("file-123", "Processing")

    assert store.status_file.exists()
    raw_statuses = json.loads(store.status_file.read_text(encoding="utf-8"))
    assert raw_statuses["file-123"]["status"] == "Processing"

    fresh_store = LocalFileStatusStore(base_dir=tmp_path)
    await fresh_store.initialize()

    assert await fresh_store.get_file_status("file-123") == "Processing"


@pytest.mark.asyncio
async def test_file_status_store_deletes_status_from_local_file(tmp_path):
    store = LocalFileStatusStore(base_dir=tmp_path)

    await store.initialize()
    await store.set_file_status("file-123", "Completed")
    await store.delete_file_status("file-123")

    assert await store.get_file_status("file-123") is None
    raw_statuses = json.loads(store.status_file.read_text(encoding="utf-8"))
    assert "file-123" not in raw_statuses


@pytest.mark.asyncio
async def test_legacy_redis_manager_alias_uses_local_file_store(tmp_path):
    store = RedisManager(base_dir=tmp_path)

    await store.initialize()
    await store.set_file_status("legacy-file", "Completed")

    assert await store.get_file_status("legacy-file") == "Completed"
    assert (tmp_path / "file_statuses.json").exists()
