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

        assert "Validation errors" in result
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

    def test_previous_annotation_included_in_correction(self):
        """Correction prompt should include the previous annotation."""
        agent = self._make_agent()
        result = agent._build_user_prompt(
            "A red circle",
            validation_errors=["[TAG_INVALID] 'Foobar' is not valid"],
            previous_annotation="Sensory-event, Foobar, (Red, Circle)",
        )

        assert "Previous annotation:" in result
        assert "Sensory-event, Foobar, (Red, Circle)" in result

    def test_no_previous_annotation_on_first_pass(self):
        """First pass should not mention previous annotation."""
        agent = self._make_agent()
        result = agent._build_user_prompt("A red circle")

        assert "Previous annotation:" not in result

    def test_no_previous_annotation_when_none(self):
        """Correction without previous_annotation should not include section."""
        agent = self._make_agent()
        result = agent._build_user_prompt(
            "A red circle",
            validation_errors=["[TAG_INVALID] error"],
            previous_annotation=None,
        )

        assert "Previous annotation:" not in result


class TestPromptSections:
    """Tests for prompt structure and sections."""

    def test_correction_workflow_in_system_prompt(self):
        """System prompt should contain the CORRECTION WORKFLOW section."""
        from src.utils.hed_comprehensive_guide import get_comprehensive_hed_guide

        guide = get_comprehensive_hed_guide(
            vocabulary_sample=["Red", "Circle", "Sensory-event"],
            extendable_tags=["Animal"],
        )

        assert "## CORRECTION WORKFLOW" in guide
        assert "TAG_INVALID" in guide
        assert "TAG_EXTENSION_INVALID" in guide
        assert "Fix ALL reported errors in a single pass" in guide

    def test_output_format_in_system_prompt(self):
        """System prompt should contain the OUTPUT FORMAT section."""
        from src.utils.hed_comprehensive_guide import get_comprehensive_hed_guide

        guide = get_comprehensive_hed_guide(
            vocabulary_sample=["Red"],
            extendable_tags=[],
        )

        assert "## OUTPUT FORMAT" in guide
        assert "Output ONLY the HED annotation string" in guide

    def test_modular_sections_assembled(self):
        """All expected sections should be present in the assembled guide."""
        from src.utils.hed_comprehensive_guide import get_comprehensive_hed_guide

        guide = get_comprehensive_hed_guide(
            vocabulary_sample=["Red", "Circle"],
            extendable_tags=["Animal"],
        )

        expected_sections = [
            "# HED ANNOTATION GUIDE",
            "## CRITICAL RULE: CHECK VOCABULARY FIRST",
            "## CORRECTION WORKFLOW",
            "## SEMANTIC GROUPING RULES",
            "## RELATION TAGS",
            "## EXTENSION RULES",
            "## DEFINITION SYSTEM",
            "## TEMPORAL SCOPING",
            "## SIDECAR SYNTAX",
            "## COMMON PATTERNS",
            "## VOCABULARY LOOKUP",
            "## COMMON ERRORS AND TROUBLESHOOTING",
            "## OUTPUT FORMAT",
        ]
        for section in expected_sections:
            assert section in guide, f"Missing section: {section}"
