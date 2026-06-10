"""
Unified LLM gateway providing a single seam for all LLM interactions.

Replaces the three parallel code paths (pipeline LLMClient, /llm/query,
/llm/query/stream) with one module. Configuration is read once from
environment variables at init time; per-call overrides are supported.

Usage:
    gateway = LLMGateway()
    # synchronous
    resp = gateway.query(system_prompt="...", user_content="...")

    # async
    resp = await gateway.query_async(...)

    # streaming (SSE generator)
    async for chunk in gateway.query_stream(...):
        yield chunk
"""

import logging
import os
from typing import AsyncIterator, Optional, Dict, Any

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

DEFAULT_API_URL = "https://api.siliconflow.cn/v1/"
DEFAULT_MODEL = "deepseek-ai/DeepSeek-V3.1"
DEFAULT_TEMPERATURE = 0.5
DEFAULT_MAX_TOKENS = 6144


class LLMGateway:
    """Singleton LLM access point. One gateway, one seam.

    Parameters
    ----------
    mock : bool
        When True, returns preset responses without calling any external API.
        Intended for tests and local development.
    mock_response : str
        The response text returned when mock=True. Defaults to a generic answer.
    """

    def __init__(self, mock: bool = False, mock_response: str = "") -> None:
        self._mock: bool = mock
        self._mock_response: str = mock_response or "This is a mock response from LLMGateway."
        self._api_url: str = os.getenv("LLM_API_URL", DEFAULT_API_URL)
        self._api_key: str = os.getenv("LLM_API_KEY", "")
        self._model: str = os.getenv("LLM_MODEL", DEFAULT_MODEL)
        self._temperature: float = float(
            os.getenv("LLM_TEMPERATURE", str(DEFAULT_TEMPERATURE))
        )
        self._max_tokens: int = int(
            os.getenv("OPENAI_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))
        )
        self._client: Optional[AsyncOpenAI] = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            if not self._api_key:
                raise RuntimeError("LLM_API_KEY is not configured")
            self._client = (
                AsyncOpenAI(api_key=self._api_key, base_url=self._api_url)
                if self._api_url
                else AsyncOpenAI(api_key=self._api_key)
            )
        return self._client

    # -- public interface ---------------------------------------------------

    def query(
        self,
        *,
        system_prompt: str = "",
        user_content: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Synchronous query. Thin wrapper around the OpenAI SDK."""
        if self._mock:
            return self._build_mock_response(user_content)
        import asyncio
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            self.query_async(
                system_prompt=system_prompt,
                user_content=user_content,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        )

    async def query_async(
        self,
        *,
        system_prompt: str = "",
        user_content: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Async query returning the raw completion model_dump."""
        if self._mock:
            return self._build_mock_response(user_content)
        client = self._get_client()
        try:
            completion = await client.chat.completions.create(
                model=model or self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=temperature if temperature is not None else self._temperature,
                max_tokens=max_tokens if max_tokens is not None else self._max_tokens,
            )
            return completion.model_dump()
        except Exception as e:
            logger.error("LLM query failed: %s", str(e), exc_info=True)
            raise

    async def query_stream(
        self,
        *,
        system_prompt: str = "",
        user_content: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """Async generator that yields SSE-formatted JSON chunks."""
        if self._mock:
            yield f"data: {self._mock_response}\n\n"
            yield "data: [DONE]\n\n"
            return
        client = self._get_client()
        try:
            stream = await client.chat.completions.create(
                model=model or self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=temperature if temperature is not None else self._temperature,
                max_tokens=max_tokens if max_tokens is not None else self._max_tokens,
                stream=True,
            )
            async for chunk in stream:
                yield f"data: {chunk.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error("LLM stream failed: %s", str(e), exc_info=True)
            raise

    def _build_mock_response(self, user_content: str) -> Dict[str, Any]:
        """Return a structured mock response resembling an OpenAI completion."""
        return {
            "id": "mock-completion-001",
            "object": "chat.completion",
            "created": 0,
            "model": "mock-model",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": self._mock_response,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": len(user_content.split()),
                "completion_tokens": len(self._mock_response.split()),
                "total_tokens": len(user_content.split()) + len(self._mock_response.split()),
            },
        }
