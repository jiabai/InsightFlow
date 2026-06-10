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

from be.common.models import FileMetadata, Chunk
from be.common.repository import InsightRepository
from be.common.file_metadata_response import FileMetadataResponse
from be.common.redis_manager import RedisManager
from be.common.storage_interface import StorageInterface
from be.common.exceptions import StorageError, DatabaseError, RedisError
from be.api_services.shared_resources import get_logger

from be.llm_knowledge_processing.llm_gateway import LLMGateway

router = APIRouter()


async def get_database_manager(request: Request) -> DatabaseManager:
    """Dependency that returns the shared DatabaseManager instance."""
    return request.app.state.db_manager

async def get_db(request: Request):
    """Dependency that yields a database session."""
    db_mgr: DatabaseManager = request.app.state.db_manager
    async with db_mgr.get_db() as db:
        yield db

async def get_redis_manager(request: Request) -> RedisManager:
    """Dependency that returns the shared RedisManager instance."""
    return request.app.state.redis_manager

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
    db_mgr: AsyncSession = Depends(get_db)
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
    llm_url = os.getenv("LLM_API_URL", "https://api.siliconflow.cn/v1/")
    if not llm_url:
        logger.error("LLM_API_URL is not configured")
        raise HTTPException(status_code=500, detail="LLM_API_URL is not configured")

    llm_key = os.getenv("LLM_API_KEY", "***REDACTED-KEY***")
    if not llm_key:
        logger.error("LLM_API_KEY is not configured")
        raise HTTPException(status_code=500, detail="LLM_API_KEY is not configured")

    model = os.getenv("LLM_MODEL", "deepseek-ai/DeepSeek-V3.1")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.4"))
    max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "5120"))

    # Fetch chunk content
    chunk = await db_manager.get_chunk_by_id(db_mgr, payload.chunk_id)
    if not chunk:
        logger.error("Chunk not found: %s", payload.chunk_id)
        raise HTTPException(status_code=404, detail=f"Chunk not found: {payload.chunk_id}")

    # Fetch question under this chunk
    questions = await db_manager.get_questions_by_chunk_id(db_mgr, payload.chunk_id)
    target_q = next((q for q in questions if q.id == payload.question_id), None)
    if not target_q:
        logger.error("Question %s not found under chunk %s", payload.question_id, payload.chunk_id)
        raise HTTPException(status_code=404, detail=f"Question not found: {payload.question_id}")

    # 组织提示词
    system_prompt = (
        "You are a helpful assistant. Answer the question using the provided context. "
        "If the answer is not in the context, share your thoughts instead of saying 'I don't know'."
    )
    user_content = (
        f"Question:\n{target_q.question}\n\n"
        f"Context:\n{chunk.content or ''}"
    )

    # 初始化 OpenAI 异步客户端（可带 base_url）
    client = (AsyncOpenAI(api_key=llm_key, base_url=llm_url)
             if llm_url else AsyncOpenAI(api_key=llm_key))

    try:
        # 调用 Chat Completions
        completion = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # 原样返回上游 JSON（FastAPI 会自动转为 JSON）
        return completion.model_dump()

    except Exception as e:
        logger.error("OpenAI API request failed: %s", str(e), exc_info=True)
        raise HTTPException(status_code=502, detail="Upstream OpenAI API error") from e

@router.post("/llm/query/stream")
async def llm_query_stream(
    payload: LLMQueryRequest,
    db_mgr: AsyncSession = Depends(get_db)
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
    llm_url = os.getenv("LLM_API_URL", "https://api.siliconflow.cn/v1/")
    if not llm_url:
        logger.error("LLM_API_URL is not configured")
        raise HTTPException(status_code=500, detail="LLM_API_URL is not configured")

    llm_key = os.getenv("LLM_API_KEY", "***REDACTED-KEY***")
    if not llm_key:
        logger.error("LLM_API_KEY is not configured")
        raise HTTPException(status_code=500, detail="LLM_API_KEY is not configured")

    model = os.getenv("LLM_MODEL", "Qwen/Qwen3-30B-A3B-Thinking-2507")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "7680"))

    # 读取上下文
    chunk = await db_manager.get_chunk_by_id(db_mgr, payload.chunk_id)
    if not chunk:
        logger.error("Chunk not found: %s", payload.chunk_id)
        raise HTTPException(status_code=404, detail=f"Chunk not found: {payload.chunk_id}")

    questions = await db_manager.get_questions_by_chunk_id(db_mgr, payload.chunk_id)
    # 通过遍历查找，避免把 Column[int] 当作字典键类型
    target_q = None
    for q in questions:
        if getattr(q, "id", None) == payload.question_id:
            target_q = q
            break

    if not target_q:
        logger.error("Question %s not found under chunk %s", payload.question_id, payload.chunk_id)
        raise HTTPException(status_code=404, detail=f"Question not found: {payload.question_id}")

    system_prompt = (
        "You are a helpful assistant. Answer the question using the provided context. "
        "If the answer is not in the context, share your thoughts instead of saying 'I don't know'."
    )
    user_content = (
        f"Question:\n{target_q.question}\n\n"
        f"Context:\n{chunk.content or ''}"
    )

    client = (AsyncOpenAI(api_key=llm_key, base_url=llm_url) 
             if llm_url else AsyncOpenAI(api_key=llm_key))

    async def sse_event_stream():
        try:
            # 开启上游流式
            stream = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            async for part in stream:
                # 直接使用上游 OpenAI 返回的原生数据
                try:
                    # 将上游的 chunk 转换为字典并直接输出
                    chunk_data = part.model_dump()
                    yield f'data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n'
                except Exception as e:
                    logger.warning("Failed to serialize chunk: %s", str(e))
                    # 如果序列化失败，尝试提取基本信息
                    try:
                        choice = part.choices[0]
                        delta = getattr(choice, "delta", None)
                        text = getattr(delta, "content", None) if delta else None
                        finish_reason = getattr(choice, "finish_reason", None)
                        
                        # 构造最小化的兼容格式
                        fallback_data = {
                            "id": getattr(part, "id", f"chatcmpl-{uuid.uuid4().hex[:8]}"),
                            "object": "chat.completion.chunk",
                            "created": getattr(part, "created", int(time.time())),
                            "model": getattr(part, "model", model),
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {"content": text} if text else {},
                                    "finish_reason": finish_reason
                                }
                            ]
                        }
                        yield f'data: {json.dumps(fallback_data, ensure_ascii=False)}\n\n'
                    except Exception:
                        # 完全失败时跳过这个chunk
                        continue
            
            # OpenAI API 标准结束标记
            yield 'data: [DONE]\n\n'

        except Exception as e:
            logger.error("OpenAI streaming failed: %s", str(e), exc_info=True)
            # 使用简化的错误格式
            error_chunk_data = {
                "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "error"
                    }
                ],
                "error": {
                    "message": str(e),
                    "type": "api_error"
                }
            }
            yield f'data: {json.dumps(error_chunk_data, ensure_ascii=False)}\n\n'
            yield 'data: [DONE]\n\n'

    # SSE 必须的响应头（根据网关/代理可再优化）
    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",  # Nginx 如有，建议禁止缓冲，加速推送
    }
    return StreamingResponse(sse_event_stream(), media_type="text/event-stream", headers=headers)

