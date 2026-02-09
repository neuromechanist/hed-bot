"""Tests for annotation agent prompt building and tag suggestion formatting.

These tests verify the pure functions in AnnotationAgent without requiring
an LLM or API calls.
"""

from src.agents.annotation_agent import AnnotationAgent


class TestFormatTagSuggestions:
    """Tests for _format_tag_suggestions method."""

    def _make_agent(self):
        """Create an AnnotationAgent without LLM (only testing pure methods)."""
        # LLM is only used by annotate(), not by the formatting methods
        agent = object.__new__(AnnotationAgent)
        return agent

    def test_empty_dict_returns_empty_string(self):
        """Empty tag_suggestions should return empty string."""
        agent = self._make_agent()
        assert agent._format_tag_suggestions({}) == ""

    def test_single_tag_with_suggestions(self):
        """Should format a single tag with its suggestions."""
        agent = self._make_agent()
        result = agent._format_tag_suggestions({"Grass": ["Green", "Item-natural-feature"]})

        assert "Grass" in result
        assert "Green" in result
        assert "Item-natural-feature" in result
        assert "Instead of" in result

    def test_tag_with_no_suggestions(self):
        """Should show fallback text when a tag has no suggestions."""
        agent = self._make_agent()
        result = agent._format_tag_suggestions({"FakeTag": []})

        assert "FakeTag" in result
        assert "no direct match" in result

    def test_mixed_tags(self):
        """Should handle mix of tags with and without suggestions."""
        agent = self._make_agent()
        result = agent._format_tag_suggestions(
            {
                "Grass": ["Green", "Item-natural-feature"],
                "FakeTag": [],
            }
        )

        assert "Grass" in result
        assert "Green" in result
        assert "FakeTag" in result
        assert "no direct match" in result

    def test_truncates_to_three_suggestions(self):
        """Should show at most 3 suggestions per tag."""
        agent = self._make_agent()
        result = agent._format_tag_suggestions(
            {
                "test": ["Tag1", "Tag2", "Tag3", "Tag4", "Tag5"],
            }
        )

        assert "Tag1" in result
        assert "Tag2" in result
        assert "Tag3" in result
        assert "Tag4" not in result
        assert "Tag5" not in result

    def test_result_is_truthy_when_populated(self):
        """Non-empty suggestions should produce a truthy string."""
        agent = self._make_agent()
        result = agent._format_tag_suggestions({"Grass": ["Green"]})
        assert result  # truthy

    def test_result_is_falsy_when_empty(self):
        """Empty suggestions should produce a falsy string."""
        agent = self._make_agent()
        result = agent._format_tag_suggestions({})
        assert not result  # falsy


class TestBuildUserPrompt:
    """Tests for _build_user_prompt method."""

    def _make_agent(self):
        """Create an AnnotationAgent without LLM (only testing pure methods)."""
        agent = object.__new__(AnnotationAgent)
        return agent

    def test_first_pass_no_errors(self):
        """First annotation pass should produce simple description prompt."""
        agent = self._make_agent()
        result = agent._build_user_prompt("A red circle appears on screen")

        assert "A red circle appears on screen" in result
        assert "Generate a HED annotation" in result
        assert "validation errors" not in result

    def test_with_errors_no_suggestions(self):
        """Errors without suggestions should not include suggestion block."""
        agent = self._make_agent()
        result = agent._build_user_prompt(
            "A red circle appears",
            validation_errors=["[TAG_INVALID] 'Grass' is not valid"],
        )

        assert "validation errors" in result
        assert "TAG_INVALID" in result
        assert "Suggested VALID HED tag" not in result
        assert "IMPORTANT: Replace" not in result

    def test_with_errors_and_suggestions(self):
        """Errors with suggestions should include both blocks."""
        agent = self._make_agent()
        result = agent._build_user_prompt(
            "A grassy field",
            validation_errors=["[TAG_INVALID] 'Grass' is not valid"],
            tag_suggestions={"Grass": ["Green", "Item-natural-feature"]},
        )

        assert "TAG_INVALID" in result
        assert "Suggested VALID HED tag" in result
        assert "Instead of 'Grass'" in result
        assert "Green" in result
        assert "IMPORTANT: Replace invalid tags" in result

    def test_with_errors_and_empty_suggestions(self):
        """Empty suggestions dict should not include suggestion block."""
        agent = self._make_agent()
        result = agent._build_user_prompt(
            "A grassy field",
            validation_errors=["[TAG_INVALID] 'Grass' is not valid"],
            tag_suggestions={},
        )

        assert "TAG_INVALID" in result
        assert "Suggested VALID HED tag" not in result
        assert "IMPORTANT: Replace" not in result

    def test_critical_output_instruction_always_present(self):
        """The CRITICAL output instruction should always be present."""
        agent = self._make_agent()

        # First pass
        result1 = agent._build_user_prompt("Test event")
        assert "CRITICAL: Output ONLY the raw HED annotation string" in result1

        # Correction pass
        result2 = agent._build_user_prompt(
            "Test event",
            validation_errors=["some error"],
        )
        assert "CRITICAL: Output ONLY the raw HED annotation string" in result2

        # Correction pass with suggestions
        result3 = agent._build_user_prompt(
            "Test event",
            validation_errors=["some error"],
            tag_suggestions={"Bad": ["Good"]},
        )
        assert "CRITICAL: Output ONLY the raw HED annotation string" in result3
