# ADR 002: Local File Status Store

Status: accepted

## Context

The backend previously used Redis to store file processing status values such as
`Pending`, `Processing`, `Completed`, and `Failed`. The product now needs status
information to be persisted locally without requiring a Redis service.

## Decision

Backend status information is stored in a local JSON file via
`server.common.file_status_store.LocalFileStatusStore`.

The default directory is `./status_store`, configurable with
`LOCAL_STATUS_STORE_DIR`. The status file is `file_statuses.json`.

The public async API remains:

- `initialize()`
- `set_file_status(file_id, status, ttl_seconds=604800)`
- `get_file_status(file_id)`
- `delete_file_status(file_id)`
- `close()`

`server.common.redis_manager.RedisManager` remains as a compatibility alias to
avoid breaking older scripts during the transition, but production code should
use `FileStatusStore` / `LocalFileStatusStore`.

## Consequences

- Redis is no longer required for backend file status tracking.
- Status data is process-local filesystem state, so deployments with multiple
  backend instances must place `LOCAL_STATUS_STORE_DIR` on shared storage or use
  another coordinated store later.
- Runtime status files are ignored by git through `status_store/`.
