"""
Compatibility import for older code paths.

InsightFlow now uses SQLite for local persistence. New production code should
import InsightSQLiteRepository directly.
"""

from server.common.insight_sqlite_repository import InsightSQLiteRepository


InsightMySQLRepository = InsightSQLiteRepository
