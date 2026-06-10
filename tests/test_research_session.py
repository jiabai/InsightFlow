"""
Test: Research Session (#07) — augmentation module.
"""
import pytest


class TestResearchSession:
    """Verify ResearchSession augmentation interface."""

    async def test_mock_augment_returns_sources(self):
        """Mock mode should return preset search results."""
        from be.llm_knowledge_processing.research_session import ResearchSession

        session = ResearchSession(mock=True)
        result = await session.augment(
            question="What is deep learning?",
            context="Deep learning is a subset of machine learning.",
        )

        assert result["error"] is None, "Mock should not produce errors"
        assert len(result["sources"]) >= 2, f"Expected ≥2 sources, got {len(result['sources'])}"
        assert len(result["enriched_context"]) > 0, "Should have enriched context"

        # Each source should have required fields
        for source in result["sources"]:
            assert "url" in source
            assert "title" in source
            assert "snippet" in source

    async def test_mock_enriched_context_has_source_annotations(self):
        """Enriched context should contain source annotations."""
        from be.llm_knowledge_processing.research_session import ResearchSession

        session = ResearchSession(mock=True)
        result = await session.augment(
            question="Test question?",
            context="Some context.",
        )

        assert "[来源:" in result["enriched_context"], (
            "Enriched context should have source annotations"
        )

    async def test_real_mode_does_not_crash(self):
        """Real mode (no API keys) should return empty results gracefully."""
        from be.llm_knowledge_processing.research_session import ResearchSession

        session = ResearchSession(mock=False)
        result = await session.augment(
            question="Any question?",
            context="Any context.",
        )

        # Should not raise, and should return a valid dict
        assert isinstance(result, dict)
        assert "sources" in result
        assert "enriched_context" in result
        # Real mode currently returns empty (not integrated yet)
        assert result["error"] is None or isinstance(result["error"], str)
