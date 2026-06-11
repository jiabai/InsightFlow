"""Backward-compatible import path for the local file status store.

Status information is now persisted locally by ``LocalFileStatusStore``. The
``RedisManager`` name remains as a compatibility alias for older scripts that
still import this module.
"""

from server.common.file_status_store import LocalFileStatusStore


class RedisManager(LocalFileStatusStore):
    """Compatibility alias for the local file-backed status store."""
