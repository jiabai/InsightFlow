"""
Test 3: LLMGateway mock mode — verifies the gateway returns preset responses
without calling any external API.
"""
import pytest


class TestLLMGatewayMock:
    """Verify LLMGateway mock mode works correctly."""

    def test_mock_query_returns_preset_response(self, mock_llm_gateway):
        """Calling query() in mock mode returns the configured mock_response."""
        result = mock_llm_gateway.query(user_content="Hello")
        assert result["choices"][0]["message"]["content"] == "This is a mock answer."

    async def test_mock_query_async_returns_preset_response(self, mock_llm_gateway):
        """Calling query_async() in mock mode returns the configured response."""
        result = await mock_llm_gateway.query_async(user_content="Hello")
        assert result["choices"][0]["message"]["content"] == "This is a mock answer."

    async def test_mock_query_stream_yields_response(self, mock_llm_gateway):
        """Calling query_stream() in mock mode yields the mock response."""
        chunks = []
        async for chunk in mock_llm_gateway.query_stream(user_content="Hello"):
            chunks.append(chunk)
        assert len(chunks) == 2
        assert chunks[0] == "data: This is a mock answer.\n\n"
        assert chunks[1] == "data: [DONE]\n\n"

    def test_custom_mock_response(self):
        """A gateway with a custom mock_response returns that string."""
        from be.llm_knowledge_processing.llm_gateway import LLMGateway
        gw = LLMGateway(mock=True, mock_response="Custom answer!")
        result = gw.query(user_content="Hi")
        assert result["choices"][0]["message"]["content"] == "Custom answer!"
