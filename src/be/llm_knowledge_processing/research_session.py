"""
Research Session integration module — wraps deepresearch_agent for
use by the streaming Q&A pipeline.

Provides a stable interface regardless of the underlying implementation.
"""
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class ResearchSession:
    """Research augmentation for streaming Q&A.

    When called, searches for additional context to enrich an LLM answer.
    If the research agent fails (no API keys, network issues), it silently
    returns empty results — the main Q&A flow continues with original context.

    Parameters
    ----------
    mock : bool
        When True, returns preset mock results without calling external APIs.
    """

    def __init__(self, mock: bool = False):
        self._mock = mock

    async def augment(
        self,
        question: str,
        context: str,
    ) -> Dict[str, Any]:
        """Search for additional context to augment a Q&A answer.

        Returns:
            dict with keys:
            - sources: list of {url, title, snippet}
            - enriched_context: str (concatenated search results)
            - error: str | None (if augmentation failed gracefully)
        """
        if self._mock:
            return self._mock_augment(question)

        try:
            return await self._real_augment(question, context)
        except Exception as e:
            logger.warning("Research augmentation failed: %s", e)
            return {
                "sources": [],
                "enriched_context": "",
                "error": str(e),
            }

    async def _real_augment(self, question: str, context: str) -> Dict[str, Any]:
        """Call the deepresearch_agent (real implementation placeholder)."""
        # TODO: Integrate deepresearch_agent when ready
        logger.info("Research augmentation not yet integrated (deepresearch_agent experimental)")
        return {
            "sources": [],
            "enriched_context": "",
            "error": None,
        }

    def _mock_augment(self, question: str) -> Dict[str, Any]:
        """Return preset mock results for testing."""
        return {
            "sources": [
                {
                    "url": "https://example.com/article1",
                    "title": "Understanding " + question[:30],
                    "snippet": "This is a mock search result about " + question[:20],
                },
                {
                    "url": "https://example.com/article2",
                    "title": "Deep dive into the topic",
                    "snippet": "Additional context from a second source.",
                },
            ],
            "enriched_context": (
                "[来源: https://example.com/article1] "
                "This is mock enriched context about " + question + ". "
                "[来源: https://example.com/article2] "
                "Additional information from secondary sources."
            ),
            "error": None,
        }
