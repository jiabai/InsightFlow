# ADR 003: SQLite Repository

Status: accepted

## Context

The backend previously used a MySQL repository for file metadata, chunks, and
generated questions. Local development should not require a separate MySQL
service, and the current scope is single-machine persistence.

## Decision

Backend database persistence uses SQLite through
`server.common.insight_sqlite_repository.InsightSQLiteRepository`.

The default database path is `./data/insight_flow.sqlite3`, configurable with
`SQLITE_DB_PATH`. Startup creates the parent directory and runs
`Base.metadata.create_all` to create the required tables.

SQLite foreign keys are enabled with `PRAGMA foreign_keys=ON`.

No automatic MySQL-to-SQLite data migration is provided.

`server.common.insight_mysql_repository.InsightMySQLRepository` remains as a
compatibility alias to avoid breaking older imports during the transition, but
production code should import `InsightSQLiteRepository` directly.

## Consequences

- MySQL is no longer required for local backend persistence.
- Runtime database files are ignored by git through `data/`.
- SQLite is appropriate for local and single-process use. Deployments with
  multiple writers may need a server database again later.
- Existing MySQL data must be exported/imported manually if it is needed.
