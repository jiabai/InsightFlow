"""Local file-backed status storage for file processing state."""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

from server.common.exceptions import StatusStoreError


class LocalFileStatusStore:
    """Persist file processing statuses to a local JSON file.

    The public async methods intentionally match the previous status manager
    contract so routes and background services can keep their flow unchanged.
    """

    def __init__(self, base_dir: str | os.PathLike[str] | None = None):
        self.base_dir = Path(base_dir or os.getenv("LOCAL_STATUS_STORE_DIR", "status_store"))
        self.status_file = self.base_dir / "file_statuses.json"
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self):
        """Create the status directory and backing JSON file when needed."""
        async with self._lock:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            if not self.status_file.exists():
                self._write_statuses({})
            self._initialized = True

    async def set_file_status(self, file_id: str, status: str, ttl_seconds: int = 604800):
        """Set the processing status for a file ID."""
        await self._ensure_initialized()
        async with self._lock:
            statuses = self._read_statuses()
            now = time.time()
            statuses[file_id] = {
                "status": status,
                "updated_at": now,
                "expires_at": now + ttl_seconds if ttl_seconds else None,
            }
            self._write_statuses(statuses)

    async def get_file_status(self, file_id: str) -> str | None:
        """Return the current status for a file ID, or None when absent/expired."""
        await self._ensure_initialized()
        async with self._lock:
            statuses = self._read_statuses()
            record = statuses.get(file_id)
            if record is None:
                return None

            if isinstance(record, str):
                return record

            expires_at = record.get("expires_at")
            if expires_at is not None and expires_at <= time.time():
                statuses.pop(file_id, None)
                self._write_statuses(statuses)
                return None

            return record.get("status")

    async def delete_file_status(self, file_id: str):
        """Delete the stored status for a file ID."""
        await self._ensure_initialized()
        async with self._lock:
            statuses = self._read_statuses()
            statuses.pop(file_id, None)
            self._write_statuses(statuses)

    async def close(self):
        """No-op close hook for lifecycle symmetry."""
        self._initialized = False

    async def close_redis(self):
        """Backward-compatible close hook for legacy callers."""
        await self.close()

    async def _ensure_initialized(self):
        if not self._initialized:
            await self.initialize()

    def _read_statuses(self) -> dict[str, Any]:
        try:
            if not self.status_file.exists():
                return {}
            raw = self.status_file.read_text(encoding="utf-8")
            if not raw.strip():
                return {}
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError) as exc:
            raise StatusStoreError(f"Failed to read file status store: {exc}") from exc

    def _write_statuses(self, statuses: dict[str, Any]):
        try:
            temp_file = self.status_file.with_suffix(".json.tmp")
            temp_file.write_text(
                json.dumps(statuses, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            temp_file.replace(self.status_file)
        except OSError as exc:
            raise StatusStoreError(f"Failed to write file status store: {exc}") from exc


FileStatusStore = LocalFileStatusStore
