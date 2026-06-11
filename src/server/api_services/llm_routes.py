"""LLM query and streaming endpoints."""

import hashlib
import asyncio
import re
import os
import time
import uuid
from typing import List
from urllib.parse import quote
import json
import traceback

from pydantic import BaseModel
from fastapi import APIRouter, Request
from fastapi import Depends, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from server.common.models import FileMetadata, Chunk
from server.common.repository import InsightRepository
from server.common.file_metadata_response import FileMetadataResponse
from server.common.file_status_store import FileStatusStore
from server.common.storage_interface import StorageInterface
from server.common.exceptions import StorageError, DatabaseError, StatusStoreError
from server.api_services.shared_resources import get_logger

from server.llm_knowledge_processing.llm_gateway import LLMGateway

router = APIRouter()


async def get_database_manager(request: Request) -> InsightRepository:
    """Dependency that returns the shared InsightRepository instance."""
    return request.app.state.db_manager

async def get_db(request: Request):
    """Dependency that yields a database session."""
    db_mgr: InsightRepository = request.app.state.db_manager
    async with db_mgr.get_db() as db:
        yield db

async def get_status_store(request: Request) -> FileStatusStore:
    """Dependency that returns the shared file status store instance."""
    return request.app.state.status_store


get_redis_manager = get_status_store

async def get_storage_manager(request: Request) -> StorageInterface:
    """Dependency that returns the shared StorageInterface instance."""
    return request.app.state.storage_manager


async def get_llm_gateway(request: Request) -> LLMGateway:
    """Dependency that returns the LLMGateway."""
    return request.app.state.llm_gateway

class LLMQueryRequest(BaseModel):
    """
    Request model for LLM query endpoints.

    This model defines the structure of requests made to LLM query endpoints,
    containing identifiers for both the question and its associated chunk context.

    Attributes:
        question_id (int): Unique identifier of the question to be answered
        chunk_id (int): Identifier of the chunk containing context for the question
    """
    question_id: int
    chunk_id: int

@router.post("/llm/query")
async def llm_query(
    payload: LLMQueryRequest,
    db_mgr: InsightRepository = Depends(get_database_manager),
    llm_gateway: LLMGateway = Depends(get_llm_gateway),
):
    """
    Process an LLM query request by retrieving context and generating a response.

    This endpoint handles LLM query requests by:
    1. Validating LLM configuration settings
    2. Retrieving chunk content and associated question
    3. Constructing prompts with context and question
    4. Making API calls to the LLM service
    
    Args:
        payload (LLMQueryRequest): Request payload containing chunk_id and question_id
        db_mgr (AsyncSession): Database session for retrieving chunks and questions

    Returns:
        dict: The raw response from the LLM API containing:
            - id: Unique identifier for the completion
            - object: Type of object returned
            - created: Timestamp of when the completion was created
            - model: Name of the model used
            - choices: List of completion choices
            - usage: Token usage statistics

    Raises:
        HTTPException:
            - 500 if LLM configuration is missing
            - 404 if chunk or question not found
            - 502 if upstream LLM API call fails
    """
    logger = get_logger()
    logger.debug(
        "llm query request question_id=%s chunk_id=%s",
        payload.question_id,
        payload.chunk_id,
    )

    async with db_mgr.get_db() as db:
        # Fetch chunk content
        chunk = await db_mgr.get_chunk_by_id(db, payload.chunk_id)
        if not chunk:
            logger.error("Chunk not found: %s", payload.chunk_id)
            raise HTTPException(status_code=404, detail=f"Chunk not found: {payload.chunk_id}")

        # Fetch question under this chunk
        questions = await db_mgr.get_questions_by_chunk_id(db, payload.chunk_id)
        target_q = next((q for q in questions if q.id == payload.question_id), None)
    if not target_q:
        logger.error("Question %s not found under chunk %s", payload.question_id, payload.chunk_id)
        raise HTTPException(status_code=404, detail=f"Question not found: {payload.question_id}")
    logger.debug(
        "llm query context ready question_id=%s chunk_id=%s context_length=%d question_length=%d",
        payload.question_id,
        payload.chunk_id,
        len(chunk.content or ""),
        len(target_q.question or ""),
    )

    # Construct prompt
    system_prompt = (
        "You are a helpful assistant. Answer the question using the provided context. "
        "If the answer is not in the context, share your thoughts instead of saying 'I don't know'."
    )
    user_content = (
        f"Question:\n{target_q.question}\n\n"
        f"Context:\n{chunk.content or ''}"
    )

    try:
        logger.debug(
            "llm query start question_id=%s chunk_id=%s",
            payload.question_id,
            payload.chunk_id,
        )
        result = await llm_gateway.query_async(
            system_prompt=system_prompt,
            user_content=user_content,
        )
        logger.debug(
            "llm query success question_id=%s chunk_id=%s",
            payload.question_id,
            payload.chunk_id,
        )
        return result
    except Exception as e:
        logger.error(
            "llm query error question_id=%s chunk_id=%s error=%s",
            payload.question_id,
            payload.chunk_id,
            str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=502, detail="LLM query failed") from e

@router.post("/llm/query/stream")
async def llm_query_stream(
    payload: LLMQueryRequest,
    db_mgr: InsightRepository = Depends(get_database_manager),
    llm_gateway: LLMGateway = Depends(get_llm_gateway),
):
    """
    Stream LLM responses for a given query request.

    This endpoint provides streaming responses from an LLM model by:
    1. Retrieving context from the specified chunk
    2. Finding the target question
    3. Constructing prompts with context and question
    4. Streaming responses from the LLM API

    Args:
        payload (LLMQueryRequest): Request payload containing chunk_id and question_id
        db_mgr (AsyncSession): Database session for retrieving chunks and questions

    Returns:
        StreamingResponse: Server-sent events stream containing:
            - LLM response chunks in OpenAI API format
            - Error messages if processing fails
            - [DONE] marker on completion

    Raises:
        HTTPException: 
            - 500 if LLM configuration is missing
            - 404 if chunk or question not found
            - 500 for other processing errors
    """
    logger = get_logger()
    logger.debug(
        "llm stream request question_id=%s chunk_id=%s",
        payload.question_id,
        payload.chunk_id,
    )

    async with db_mgr.get_db() as db:
        # Fetch chunk
        chunk = await db_mgr.get_chunk_by_id(db, payload.chunk_id)
        if not chunk:
            logger.error("Chunk not found: %s", payload.chunk_id)
            raise HTTPException(status_code=404, detail=f"Chunk not found: {payload.chunk_id}")

        # Find target question
        questions = await db_mgr.get_questions_by_chunk_id(db, payload.chunk_id)
        target_q = None
        for q in questions:
            if getattr(q, "id", None) == payload.question_id:
                target_q = q
                break
    if not target_q:
        logger.error("Question %s not found under chunk %s", payload.question_id, payload.chunk_id)
        raise HTTPException(status_code=404, detail=f"Question not found: {payload.question_id}")
    logger.debug(
        "llm stream context ready question_id=%s chunk_id=%s context_length=%d question_length=%d",
        payload.question_id,
        payload.chunk_id,
        len(chunk.content or ""),
        len(target_q.question or ""),
    )

    # Try research augmentation (graceful degradation)
    enriched = ""
    try:
        from server.llm_knowledge_processing.research_session import ResearchSession
        rs = ResearchSession(mock=getattr(llm_gateway, '_mock', False))
        aug_result = await rs.augment(
            question=target_q.question,
            context=chunk.content or "",
        )
        if aug_result.get("enriched_context"):
            enriched = "\n\nAdditional Context from Research:\n" + aug_result["enriched_context"]
    except Exception as e:
        logger.warning("Research augmentation unavailable: %s", e)

    system_prompt = (
        "You are a helpful assistant. Answer the question using the provided context. "
        "If the answer is not in the context, share your thoughts instead of saying 'I don't know'."
    )
    user_content = (
        f"Question:\n{target_q.question}\n\n"
        f"Context:\n{chunk.content or ''}"
        f"{enriched}"
    )

    async def logged_stream():
        logger.debug(
            "llm stream start question_id=%s chunk_id=%s",
            payload.question_id,
            payload.chunk_id,
        )
        try:
            async for chunk_data in llm_gateway.query_stream(
                system_prompt=system_prompt,
                user_content=user_content,
            ):
                yield chunk_data
            logger.debug(
                "llm stream end question_id=%s chunk_id=%s",
                payload.question_id,
                payload.chunk_id,
            )
        except Exception as e:
            logger.error(
                "llm stream error question_id=%s chunk_id=%s error=%s",
                payload.question_id,
                payload.chunk_id,
                str(e),
                exc_info=True,
            )
            raise

    return StreamingResponse(logged_stream(), media_type="text/event-stream")

