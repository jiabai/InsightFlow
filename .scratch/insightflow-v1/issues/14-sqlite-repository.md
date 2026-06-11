# 14 - SQLite Repository
Status: completed

## Parent

`.scratch/insightflow-v1/PRD.md`

## What to change

Backend file metadata, chunks, and generated questions should be stored in
SQLite instead of MySQL. The repository interface remains unchanged so routes
and background processing continue to depend on `InsightRepository`.

## Acceptance criteria

- [x] Production startup uses `InsightSQLiteRepository`.
- [x] The SQLite database defaults to `data/insight_flow.sqlite3`.
- [x] `SQLITE_DB_PATH` can override the database file path.
- [x] First startup creates the database directory and required tables.
- [x] SQLite foreign key enforcement is enabled.
- [x] MySQL runtime dependencies are removed from `requirements.txt`.
- [x] Local SQLite database files are ignored by git.
- [x] No MySQL-to-SQLite migration is provided.
- [x] Architecture decision is documented in `docs/adr/`.

## Comments

- Implemented on 2026-06-11 with `InsightSQLiteRepository`.
- `InsightMySQLRepository` remains only as a compatibility alias for older
  imports; production code imports `InsightSQLiteRepository` directly.
