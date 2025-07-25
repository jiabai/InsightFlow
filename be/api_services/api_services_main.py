"""
FastAPI application for file management services.

This module provides the main FastAPI application setup and configuration 
for the file management
microservice. It includes:
- CORS middleware configuration
- Database, Redis and Storage manager initialization 
- Logging setup
- Router registration
- Shutdown event handlers

The service exposes REST endpoints for file management operations 
through the file_management_router.
"""

import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from be.api_services.fastpai_logger import setup_logging
from be.common.database_manager import DatabaseManager
from be.common.redis_manager import RedisManager
from be.common.storage_manager import StorageManager

from be.api_services.file_management_service import router as file_management_router

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup logging
logger = setup_logging(app, log_file='file_management.log', level=logging.DEBUG)

# Initialize managers
db_manager = DatabaseManager()
redis_manager = RedisManager()
storage_manager = StorageManager()

@app.on_event("shutdown")
async def shutdown():
    """
    Shutdown event handler that performs cleanup operations.
    
    This function is called when the FastAPI application shuts down.
    It ensures proper cleanup by:
    - Disposing the database engine connection pool
    - Closing the Redis client connection and waiting for it to complete
    """
    if db_manager.engine:
        await db_manager.engine.dispose()
    if redis_manager.redis_client:
        await redis_manager.redis_client.close()
        await redis_manager.redis_client.wait_closed()

# Include the router from file_management_service.py
app.include_router(file_management_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
