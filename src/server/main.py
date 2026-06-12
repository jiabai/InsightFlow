"""
FastAPI application for file management services.

This module provides the main FastAPI application setup and configuration 
for the file management
microservice. It includes:
- CORS middleware configuration
- Database, local status store and Storage manager initialization
- Logging setup
- Router registration
- Shutdown event handlers

The service exposes REST endpoints for file management operations 
through the file_management_router.
"""
import os
from pathlib import Path

# 加载 src/.env 到系统环境变量（必须在其他导入之前执行）
from dotenv import load_dotenv
_env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=_env_path)

import uvicorn
from fastapi.middleware.cors import CORSMiddleware

from server.api_services.shared_resources import app
from server.api_services.file_routes import router as file_router
from server.api_services.question_routes import router as question_router
from server.api_services.llm_routes import router as llm_router

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


@app.get("/healthz", include_in_schema=False)
async def healthz():
    """Lightweight health check for systemd, Nginx, and deployment smoke tests."""
    return {"status": "ok"}


if __name__ == "__main__":
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
