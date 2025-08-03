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
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

from be.api_services import shared_resources
from be.api_services.shared_resources import get_logger, app
from be.api_services.file_routes import router as file_router

logger = get_logger()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    """
    Startup event handler that initializes shared resources.

    This function is called when the FastAPI application starts up.
    It ensures that the necessary resources (database, Redis, storage)
    are initialized before the application handles any requests.
    """
    await shared_resources.init_resources()
    logger.info("startup event handler.")

@app.on_event("shutdown")
async def shutdown():
    """
    Shutdown event handler that performs cleanup operations.

    This function is called when the FastAPI application shuts down.
    It ensures proper cleanup by:
    - Disposing the database engine connection pool
    - Closing the Redis client connection and waiting for it to complete
    """
    await shared_resources.close_resources()
    logger.info("shutdown event handler.")

# # Include the router from file_management_service.py
app.include_router(file_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
