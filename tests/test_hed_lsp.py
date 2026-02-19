"""Tests for HED-LSP CLI integration module.

These tests verify the hed-lsp CLI wrapper functionality without
requiring the full HED tools stack (hedtools) to be installed.
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from src.validation.hed_lsp import (
    HedLspClient,
    HedSuggestion,
    HedSuggestResult,
    get_default_max_results,
    get_default_schema_version,
    get_default_use_semantic,
    get_hed_suggestions,
    is_hed_lsp_available,
    suggest_tags_for_keywords,
)


class TestIsHedLspAvailable:
    """Tests for is_hed_lsp_available function."""

    def test_returns_false_when_not_in_path(self):
        """Should return False when hed-suggest is not in PATH."""
        with patch("shutil.which", return_value=None):
            assert is_hed_lsp_available() is False

    def test_returns_true_when_in_path(self):
        """Should return True when hed-suggest is in PATH."""
        with patch("shutil.which", return_value="/usr/local/bin/hed-suggest"):
            assert is_hed_lsp_available() is True


class TestEnvironmentDefaults:
    """Tests for environment variable defaults."""

    def test_default_schema_version(self):
        """Should return default schema version."""
        with patch.dict("os.environ", {}, clear=True):
            assert get_default_schema_version() == "8.4.0"

    def test_schema_version_from_env(self):
        """Should return schema version from environment."""
        with patch.dict("os.environ", {"HED_SCHEMA_VERSION": "8.4.0"}):
            assert get_default_schema_version() == "8.4.0"

    def test_default_use_semantic(self):
        """Should return False by default for semantic search."""
        with patch.dict("os.environ", {}, clear=True):
            assert get_default_use_semantic() is False

    def test_use_semantic_from_env(self):
        """Should return True when env var is 'true'."""
        with patch.dict("os.environ", {"HED_LSP_USE_SEMANTIC": "true"}):
            assert get_default_use_semantic() is True

    def test_default_max_results(self):
        """Should return 10 by default."""
        with patch.dict("os.environ", {}, clear=True):
            assert get_default_max_results() == 10

    def test_max_results_from_env(self):
        """Should return value from environment."""
        with patch.dict("os.environ", {"HED_LSP_MAX_RESULTS": "20"}):
            assert get_default_max_results() == 20

    def test_max_results_invalid_value(self):
        """Should return default when env var is invalid."""
        with patch.dict("os.environ", {"HED_LSP_MAX_RESULTS": "invalid"}):
            assert get_default_max_results() == 10


class TestHedSuggestion:
    """Tests for HedSuggestion dataclass."""

    def test_create_with_tag_only(self):
        """Should create suggestion with just a tag."""
        suggestion = HedSuggestion(tag="Event/Sensory-event")
        assert suggestion.tag == "Event/Sensory-event"
        assert suggestion.score is None
        assert suggestion.description is None

    def test_create_with_all_fields(self):
        """Should create suggestion with all fields."""
        suggestion = HedSuggestion(
            tag="Event/Sensory-event",
            score=0.95,
            description="A sensory event",
        )
        assert suggestion.tag == "Event/Sensory-event"
        assert suggestion.score == 0.95
        assert suggestion.description == "A sensory event"


class TestHedSuggestResult:
    """Tests for HedSuggestResult dataclass."""

    def test_success_result(self):
        """Should create successful result."""
        result = HedSuggestResult(
            success=True,
            suggestions=[HedSuggestion(tag="Event")],
        )
        assert result.success is True
        assert len(result.suggestions) == 1
        assert result.error is None

    def test_error_result(self):
        """Should create error result."""
        result = HedSuggestResult(
            success=False,
            suggestions=[],
            error="Command failed",
        )
        assert result.success is False
        assert len(result.suggestions) == 0
        assert result.error == "Command failed"


class TestHedLspClient:
    """Tests for HedLspClient class."""

    def test_raises_when_not_available(self):
        """Should raise RuntimeError when hed-suggest not available."""
        with patch("src.validation.hed_lsp.is_hed_lsp_available", return_value=False):
            with pytest.raises(RuntimeError, match="hed-suggest CLI not found"):
                HedLspClient()

    def test_initializes_with_defaults(self):
        """Should initialize with environment defaults."""
        with (
            patch("src.validation.hed_lsp.is_hed_lsp_available", return_value=True),
            patch.dict("os.environ", {"HED_SCHEMA_VERSION": "8.4.0"}),
        ):
            client = HedLspClient()
            assert client.schema_version == "8.4.0"
            assert client.use_semantic is False
            assert client.max_results == 10

    def test_initializes_with_custom_values(self):
        """Should initialize with custom values."""
        with patch("src.validation.hed_lsp.is_hed_lsp_available", return_value=True):
            client = HedLspClient(
                schema_version="8.3.0",
                use_semantic=True,
                max_results=5,
            )
            assert client.schema_version == "8.3.0"
            assert client.use_semantic is True
            assert client.max_results == 5

    def test_suggest_empty_queries(self):
        """Should return error for empty queries."""
        with patch("src.validation.hed_lsp.is_hed_lsp_available", return_value=True):
            client = HedLspClient()
            result = client.suggest()
            assert result.success is False
            assert result.error == "No queries provided"

    def test_suggest_success(self):
        """Should return suggestions on successful CLI call."""
        mock_output = '[{"tag": "Event/Sensory-event", "score": 0.9}]'
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = mock_output
        mock_result.stderr = ""

        with (
            patch("src.validation.hed_lsp.is_hed_lsp_available", return_value=True),
            patch("subprocess.run", return_value=mock_result),
        ):
            client = HedLspClient()
            result = client.suggest("sensory event")

            assert result.success is True
            assert len(result.suggestions) == 1
            assert result.suggestions[0].tag == "Event/Sensory-event"

    def test_suggest_query_keyed_format(self):
        """Should parse query-keyed output format from hed-suggest CLI."""
        # This is the actual format returned by hed-suggest --json
        mock_output = '{"button press": ["Button", "Response-button", "Mouse-button"]}'
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = mock_output
        mock_result.stderr = ""

        with (
            patch("src.validation.hed_lsp.is_hed_lsp_available", return_value=True),
            patch("subprocess.run", return_value=mock_result),
        ):
            client = HedLspClient()
            result = client.suggest("button press")

            assert result.success is True
            assert len(result.suggestions) == 3
            assert result.suggestions[0].tag == "Button"
            assert result.suggestions[1].tag == "Response-button"
            assert result.suggestions[2].tag == "Mouse-button"

    def test_suggest_handles_timeout(self):
        """Should handle subprocess timeout."""
        with (
            patch("src.validation.hed_lsp.is_hed_lsp_available", return_value=True),
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 30)),
        ):
            client = HedLspClient()
            result = client.suggest("test")

            assert result.success is False
            assert "timed out" in result.error

    def test_suggest_handles_cli_error(self):
        """Should handle CLI error."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error: invalid schema"

        with (
            patch("src.validation.hed_lsp.is_hed_lsp_available", return_value=True),
            patch("subprocess.run", return_value=mock_result),
        ):
            client = HedLspClient()
            result = client.suggest("test")

            assert result.success is False
            assert "invalid schema" in result.error


class TestGetHedSuggestions:
    """Tests for get_hed_suggestions convenience function."""

    def test_returns_tag_strings(self):
        """Should return list of tag strings."""
        mock_output = '["Event/Sensory-event", "Event/Agent-action"]'
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = mock_output

        with (
            patch("src.validation.hed_lsp.is_hed_lsp_available", return_value=True),
            patch("subprocess.run", return_value=mock_result),
        ):
            tags = get_hed_suggestions("button press")
            assert "Event/Sensory-event" in tags

    def test_raises_on_failure(self):
        """Should raise RuntimeError on failure."""
        with patch("src.validation.hed_lsp.is_hed_lsp_available", return_value=False):
            with pytest.raises(RuntimeError, match="hed-suggest CLI not found"):
                get_hed_suggestions("test")


class TestSuggestTagsForKeywords:
    """Tests for suggest_tags_for_keywords function."""

    def test_returns_empty_for_empty_keywords(self):
        """Should return empty dict for empty keywords list."""
        with patch("src.validation.hed_lsp.is_hed_lsp_available", return_value=True):
            result = suggest_tags_for_keywords([])
            assert result == {}

    def test_returns_mapping(self):
        """Should return mapping of keywords to suggestions."""
        mock_output = '["Event/Sensory-event"]'
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = mock_output

        with (
            patch("src.validation.hed_lsp.is_hed_lsp_available", return_value=True),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = suggest_tags_for_keywords(["button", "press"])
            assert "button" in result
            assert "press" in result


class TestSuggestForDescription:
    """Tests for suggest_for_description method."""

    def _make_mock_run(self, stdout='["Event"]'):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = stdout
        mock_result.stderr = ""
        return mock_result

    def test_basic_mode_excludes_semantic_flag(self):
        """mode='basic' should not include --semantic even when use_semantic=True."""
        with (
            patch("src.validation.hed_lsp.is_hed_lsp_available", return_value=True),
            patch("subprocess.run", return_value=self._make_mock_run()) as mock_run,
        ):
            client = HedLspClient(use_semantic=True)
            client.suggest_for_description("button press", mode="basic")
            cmd = mock_run.call_args[0][0]
            assert "--semantic" not in cmd

    def test_semantic_mode_includes_semantic_flag(self):
        """mode='semantic' should include --semantic even when use_semantic=False."""
        with (
            patch("src.validation.hed_lsp.is_hed_lsp_available", return_value=True),
            patch("subprocess.run", return_value=self._make_mock_run()) as mock_run,
        ):
            client = HedLspClient(use_semantic=False)
            client.suggest_for_description("button press", mode="semantic")
            cmd = mock_run.call_args[0][0]
            assert "--semantic" in cmd

    def test_none_mode_uses_instance_default(self):
        """mode=None should use the instance's use_semantic setting."""
        with (
            patch("src.validation.hed_lsp.is_hed_lsp_available", return_value=True),
            patch("subprocess.run", return_value=self._make_mock_run()) as mock_run,
        ):
            client = HedLspClient(use_semantic=True)
            client.suggest_for_description("button press")
            cmd = mock_run.call_args[0][0]
            assert "--semantic" in cmd

    def test_does_not_mutate_use_semantic(self):
        """suggest_for_description must not mutate self.use_semantic (thread-safety)."""
        with (
            patch("src.validation.hed_lsp.is_hed_lsp_available", return_value=True),
            patch("subprocess.run", return_value=self._make_mock_run()),
        ):
            client = HedLspClient(use_semantic=False)
            client.suggest_for_description("button press", mode="semantic")
            assert client.use_semantic is False  # unchanged


class TestSuggestEmptyTagFiltering:
    """Tests for empty-tag filtering in suggest()."""

    def test_filters_empty_string_tags(self):
        """Suggestions with empty tag strings should be filtered out."""
        mock_output = '[{"tag": "", "score": 0.5}, {"tag": "Event", "score": 0.9}]'
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = mock_output
        mock_result.stderr = ""

        with (
            patch("src.validation.hed_lsp.is_hed_lsp_available", return_value=True),
            patch("subprocess.run", return_value=mock_result),
        ):
            client = HedLspClient()
            result = client.suggest("test")

            assert result.success is True
            assert len(result.suggestions) == 1
            assert result.suggestions[0].tag == "Event"

    def test_json_decode_error_returns_failure(self):
        """Invalid JSON from CLI should return failure result with JSON in error message."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not valid json {"
        mock_result.stderr = ""

        with (
            patch("src.validation.hed_lsp.is_hed_lsp_available", return_value=True),
            patch("subprocess.run", return_value=mock_result),
        ):
            client = HedLspClient()
            result = client.suggest("test")

            assert result.success is False
            assert "JSON" in result.error
