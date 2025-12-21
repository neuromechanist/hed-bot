"""Unit tests for OpenRouter LLM utility."""


class TestCreateOpenRouterLLM:
    """Tests for create_openrouter_llm function."""

    def test_creates_llm_with_default_params(self):
        """Test creating LLM with default parameters."""
        from src.utils.openrouter_llm import create_openrouter_llm

        llm = create_openrouter_llm(api_key="test-key")

        assert llm is not None
        assert llm.model_name == "openai/gpt-oss-120b"
        assert llm.temperature == 0.1

    def test_creates_llm_with_custom_model(self):
        """Test creating LLM with custom model."""
        from src.utils.openrouter_llm import create_openrouter_llm

        llm = create_openrouter_llm(model="anthropic/claude-3-haiku", api_key="test-key")

        assert llm.model_name == "anthropic/claude-3-haiku"

    def test_creates_llm_with_provider(self):
        """Test creating LLM with provider preference."""
        from src.utils.openrouter_llm import create_openrouter_llm

        llm = create_openrouter_llm(
            api_key="test-key",
            provider="Cerebras",
        )

        assert llm is not None
        # Provider is passed in extra_body
        assert llm.extra_body is not None
        assert llm.extra_body.get("provider") == {"only": ["Cerebras"]}

    def test_creates_llm_with_user_id(self):
        """Test creating LLM with user_id for cache optimization."""
        from src.utils.openrouter_llm import create_openrouter_llm

        llm = create_openrouter_llm(
            api_key="test-key",
            user_id="test-user-123",
        )

        assert llm is not None
        # User ID is passed in extra_body for sticky cache routing
        assert llm.extra_body is not None
        assert llm.extra_body.get("user") == "test-user-123"

    def test_creates_llm_with_provider_and_user_id(self):
        """Test creating LLM with both provider and user_id."""
        from src.utils.openrouter_llm import create_openrouter_llm

        llm = create_openrouter_llm(
            api_key="test-key",
            provider="Cerebras",
            user_id="test-user-456",
        )

        assert llm is not None
        assert llm.extra_body is not None
        assert llm.extra_body.get("provider") == {"only": ["Cerebras"]}
        assert llm.extra_body.get("user") == "test-user-456"

    def test_creates_llm_without_extra_body(self):
        """Test creating LLM without provider or user_id."""
        from src.utils.openrouter_llm import create_openrouter_llm

        llm = create_openrouter_llm(api_key="test-key")

        # extra_body should be None when no provider or user_id
        assert llm.extra_body is None

    def test_creates_llm_with_max_tokens(self):
        """Test creating LLM with max_tokens."""
        from src.utils.openrouter_llm import create_openrouter_llm

        llm = create_openrouter_llm(
            api_key="test-key",
            max_tokens=1000,
        )

        assert llm.max_tokens == 1000


class TestGetModelName:
    """Tests for get_model_name function."""

    def test_get_known_model_alias(self):
        """Test getting model name for known alias."""
        from src.utils.openrouter_llm import get_model_name

        result = get_model_name("gpt-oss-120b")

        assert result == "openai/gpt-oss-120b"

    def test_get_unknown_model_returns_input(self):
        """Test getting model name for unknown alias returns input."""
        from src.utils.openrouter_llm import get_model_name

        result = get_model_name("some-unknown-model")

        assert result == "some-unknown-model"
