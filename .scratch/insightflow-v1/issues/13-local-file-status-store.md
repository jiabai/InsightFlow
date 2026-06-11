# 13 - Local File Status Store
Status: completed

## Parent

`.scratch/insightflow-v1/PRD.md`

## What to change

Backend file processing status should no longer be stored in Redis. Store status
information in a local file instead, while preserving the existing async status
API used by routes and background processing.

## Acceptance criteria

- [x] Status values persist to a local JSON file.
- [x] Status values can be read by a fresh store instance.
- [x] Status deletion removes the local record.
- [x] FastAPI startup initializes the local status store instead of Redis.
- [x] Upload, delete, status, and question routes depend on `status_store`.
- [x] Runtime status files are ignored by git.
- [x] Architecture decision is documented in `docs/adr/`.

## Comments

- Implemented on 2026-06-11 with `LocalFileStatusStore`.
- `RedisManager` remains as a compatibility alias for older scripts, but
  production code now imports `FileStatusStore`.
