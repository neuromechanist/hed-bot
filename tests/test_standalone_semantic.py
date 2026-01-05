"""Standalone integration tests for semantic search.

These tests can run in feature branches without deployed backend.
They use OPENROUTER_API_KEY_FOR_TESTING for real LLM calls.

Run with: uv run python -m pytest tests/test_standalone_semantic.py -v -m standalone

Or to run all standalone tests:
    uv run python -m pytest -m standalone -v
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Use same model pattern as integration tests for consistency
TEST_MODEL = os.getenv("ANNOTATION_MODEL", "mistralai/mistral-small-3.2-24b-instruct")
TEST_PROVIDER = os.getenv("ANNOTATION_PROVIDER", "mistral")

# Skip all tests if API key not available
pytestmark = [
    pytest.mark.standalone,
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("OPENROUTER_API_KEY_FOR_TESTING"),
        reason="OPENROUTER_API_KEY_FOR_TESTING not set",
    ),
]


@pytest.fixture
def api_key():
    """Get API key for testing."""
    return os.environ.get("OPENROUTER_API_KEY_FOR_TESTING")


@pytest.fixture
def embeddings_dir():
    """Get path to embeddings directory."""
    return Path(__file__).parent.parent / "data"


@pytest.fixture
def fast_llm(api_key):
    """Create LLM for testing using env-configured model."""
    from src.utils.litellm_llm import create_litellm_openrouter

    return create_litellm_openrouter(
        model=TEST_MODEL,
        api_key=api_key,
        temperature=0.0,
        provider=TEST_PROVIDER if TEST_PROVIDER else None,
    )


class TestKeywordExtractionAgent:
    """Tests for KeywordExtractionAgent with real LLM calls."""

    @pytest.mark.asyncio
    async def test_extract_keywords_simple(self, fast_llm):
        """Extract keywords from simple description."""
        from src.agents.keyword_extraction_agent import KeywordExtractionAgent

        agent = KeywordExtractionAgent(fast_llm)
        keywords = await agent.extract("A mouse pressed a button to receive a reward")

        assert isinstance(keywords, list)
        assert len(keywords) > 0
        # Should extract relevant terms
        keyword_set = {k.lower() for k in keywords}
        assert any(term in keyword_set for term in ["mouse", "button", "press", "reward"])

    @pytest.mark.asyncio
    async def test_extract_keywords_clinical(self, fast_llm):
        """Extract keywords from clinical EEG description."""
        from src.agents.keyword_extraction_agent import KeywordExtractionAgent

        agent = KeywordExtractionAgent(fast_llm)
        keywords = await agent.extract(
            "Patient exhibited seizure activity with spike-wave discharges during sleep stage N2"
        )

        assert isinstance(keywords, list)
        assert len(keywords) > 0
        keyword_set = {k.lower() for k in keywords}
        # Should extract clinical terms
        assert any(
            term in keyword_set for term in ["seizure", "spike", "wave", "sleep", "n2", "patient"]
        )


class TestSemanticSearchWithEmbeddings:
    """Tests for semantic search with loaded embeddings."""

    def test_load_embeddings_from_directory(self, embeddings_dir):
        """Load all embeddings files from data directory."""
        from src.utils.semantic_search import SemanticSearchManager

        manager = SemanticSearchManager()

        if not embeddings_dir.exists():
            pytest.skip("Embeddings directory not found")

        result = manager.load_embeddings(embeddings_dir)
        assert result is True

        stats = manager.get_stats()
        assert stats["tag_embeddings"] > 4000  # Base + SCORE + LANG
        assert stats["keyword_embeddings"] > 400
        assert len(stats["loaded_files"]) >= 3

    def test_semantic_search_reward(self, embeddings_dir):
        """Search for reward-related tags."""
        from src.utils.semantic_search import SemanticSearchManager

        manager = SemanticSearchManager()
        if not embeddings_dir.exists():
            pytest.skip("Embeddings directory not found")
        manager.load_embeddings(embeddings_dir)

        results = manager.find_similar(["reward", "delivery"], top_k=10, use_embeddings=True)

        assert len(results) > 0
        tags = [r.tag for r in results]
        assert "Reward" in tags

    def test_semantic_search_seizure(self, embeddings_dir):
        """Search for seizure-related tags (SCORE library)."""
        from src.utils.semantic_search import SemanticSearchManager

        manager = SemanticSearchManager()
        if not embeddings_dir.exists():
            pytest.skip("Embeddings directory not found")
        manager.load_embeddings(embeddings_dir)

        results = manager.find_similar(["seizure", "epileptic"], top_k=10, use_embeddings=True)

        assert len(results) > 0
        # Should include SCORE library tags
        prefixed_tags = [(r.prefix, r.tag) for r in results]
        assert any(prefix == "sc:" for prefix, _ in prefixed_tags)


class TestFullSemanticPipeline:
    """End-to-end tests for keyword extraction -> semantic search pipeline."""

    @pytest.mark.asyncio
    async def test_pipeline_neuroscience_description(self, fast_llm, embeddings_dir):
        """Full pipeline: extract keywords then find relevant tags."""
        from src.agents.keyword_extraction_agent import KeywordExtractionAgent
        from src.utils.semantic_search import SemanticSearchManager

        if not embeddings_dir.exists():
            pytest.skip("Embeddings directory not found")

        # Step 1: Extract keywords with LLM
        keyword_agent = KeywordExtractionAgent(fast_llm)
        keywords = await keyword_agent.extract(
            "Visual stimulus presented on screen while subject fixates on cross"
        )

        assert len(keywords) > 0
        print(f"Extracted keywords: {keywords}")

        # Step 2: Load embeddings and search
        manager = SemanticSearchManager()
        manager.load_embeddings(embeddings_dir)

        results = manager.find_similar(keywords, top_k=10, use_embeddings=True)

        assert len(results) > 0
        print(f"Found {len(results)} relevant tags:")
        for r in results[:5]:
            print(f"  - {r.prefix}{r.tag} (score={r.score:.2f})")

        # Verify relevant tags found
        tags = [r.tag for r in results]
        # Should find visual/stimulus related tags
        assert any(
            t in tags for t in ["Visual-presentation", "See", "Experimental-stimulus", "Fixate"]
        )

    @pytest.mark.asyncio
    async def test_pipeline_clinical_description(self, fast_llm, embeddings_dir):
        """Full pipeline with clinical description (SCORE tags)."""
        from src.agents.keyword_extraction_agent import KeywordExtractionAgent
        from src.utils.semantic_search import SemanticSearchManager

        if not embeddings_dir.exists():
            pytest.skip("Embeddings directory not found")

        keyword_agent = KeywordExtractionAgent(fast_llm)
        keywords = await keyword_agent.extract("Sleep spindle detected during N2 sleep stage")

        assert len(keywords) > 0
        print(f"Extracted keywords: {keywords}")

        manager = SemanticSearchManager()
        manager.load_embeddings(embeddings_dir)

        results = manager.find_similar(keywords, top_k=10, use_embeddings=True)

        assert len(results) > 0
        print(f"Found {len(results)} relevant tags:")
        for r in results[:5]:
            print(f"  - {r.prefix}{r.tag} (score={r.score:.2f})")

        # Should find SCORE library sleep tags
        prefixed = [(r.prefix, r.tag) for r in results]
        has_score_tag = any(prefix == "sc:" for prefix, _ in prefixed)
        assert has_score_tag, "Should find SCORE library tags for clinical description"
