"""
Main entry point for the knowledge processing service.
This module initializes and runs the knowledge processing service
in an asyncio event loop, handling startup and shutdown gracefully.
"""
import asyncio
from be.llm_knowledge_processing.knowledge_processing_service import KnowledgeProcessingService

if __name__ == "__main__":
    service = KnowledgeProcessingService(file_id="123")
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(service.run())
    finally:
        loop.run_until_complete(service.shutdown())
        loop.close()
