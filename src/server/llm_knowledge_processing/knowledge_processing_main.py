"""
Main entry point for the knowledge processing service (standalone CLI).

This module initialises and runs the knowledge processing service
in an asyncio event loop, handling startup and shutdown gracefully.
It creates database and status store resources independently (without
FastAPI app.state).
"""
import asyncio

from server.common.insight_sqlite_repository import InsightSQLiteRepository
from server.common.file_status_store import FileStatusStore
from server.llm_knowledge_processing.knowledge_processing_service import KnowledgeProcessingService

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python knowledge_processing_main.py <user_id> <file_id>")
        sys.exit(1)

    db_manager = InsightSQLiteRepository()
    status_store = FileStatusStore()

    service = KnowledgeProcessingService(
        user_id=sys.argv[1],
        file_id=sys.argv[2],
        db_manager=db_manager,
        status_store=status_store,
    )
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(service.run())
    finally:
        loop.run_until_complete(service.shutdown())
        loop.close()
