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

from be.api_services.shared_resources import app
from be.api_services.file_routes import router as file_router
from be.api_services.question_routes import router as question_router
from be.api_services.llm_routes import router as llm_router

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(file_router)
app.include_router(question_router)
app.include_router(llm_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
