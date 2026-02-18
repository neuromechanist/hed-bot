"""Tests for the hedtools.org REST API validator."""

import pytest

from src.validation.hedtools_validator import (
    HedToolsAPIValidator,
    is_hedtools_available,
)


class TestHedToolsAvailability:
    """Tests for connectivity check."""

    @pytest.mark.integration
    def test_hedtools_is_reachable(self):
        """hedtools.org should be reachable with internet access."""
        assert is_hedtools_available() is True

    def test_hedtools_unreachable_bad_url(self):
        """Unreachable URL should return False."""
        assert is_hedtools_available(base_url="https://nonexistent.invalid") is False

    def test_hedtools_timeout(self):
        """Very short timeout should still return a boolean."""
        result = is_hedtools_available(timeout=0.001)
        # May or may not be False depending on connection speed
        assert isinstance(result, bool)


class TestHedToolsSessionInfo:
    """Tests for CSRF session handling."""

    @pytest.mark.integration
    def test_get_session_info(self):
        """Should obtain session cookie and CSRF token."""
        validator = HedToolsAPIValidator()
        cookie, csrf_token = validator._get_session_info()

        assert cookie is not None
        assert len(cookie) > 0
        assert csrf_token is not None
        assert len(csrf_token) > 0

    @pytest.mark.integration
    def test_session_caching(self):
        """Session info should be cached on second call."""
        validator = HedToolsAPIValidator()
        cookie1, csrf1 = validator._get_session_info()
        cookie2, csrf2 = validator._get_session_info()

        # Should return cached values
        assert cookie1 == cookie2
        assert csrf1 == csrf2

    def test_session_error_bad_url(self):
        """Bad URL should produce SESSION_ERROR in validation result."""
        validator = HedToolsAPIValidator(base_url="https://nonexistent.invalid")
        result = validator.validate("Sensory-event")

        assert result.is_valid is False
        assert len(result.errors) > 0


class TestHedToolsValidation:
    """Integration tests for actual validation against hedtools.org."""

    @pytest.mark.integration
    def test_valid_simple_string(self):
        """Simple valid HED string should pass validation."""
        validator = HedToolsAPIValidator(schema_version="8.4.0")
        result = validator.validate("Sensory-event")

        assert result.is_valid is True
        assert len(result.errors) == 0

    @pytest.mark.integration
    def test_valid_complex_string(self):
        """Complex valid HED string with grouping should pass."""
        validator = HedToolsAPIValidator(schema_version="8.4.0")
        result = validator.validate("Sensory-event, Visual-presentation, (Red, Circle)")

        assert result.is_valid is True
        assert len(result.errors) == 0

    @pytest.mark.integration
    def test_invalid_tag(self):
        """Invalid tag should fail validation with errors."""
        validator = HedToolsAPIValidator(schema_version="8.4.0")
        result = validator.validate("CompletelyInvalidTag123")

        assert result.is_valid is False
        assert len(result.errors) > 0

    @pytest.mark.integration
    def test_invalid_extension(self):
        """Invalid extension of non-extendable tag should fail."""
        validator = HedToolsAPIValidator(schema_version="8.4.0")
        result = validator.validate("Event/CustomEvent")

        assert result.is_valid is False
        assert len(result.errors) > 0

    @pytest.mark.integration
    def test_result_structure(self):
        """ValidationResult should have expected fields."""
        validator = HedToolsAPIValidator(schema_version="8.4.0")
        result = validator.validate("Sensory-event")

        assert hasattr(result, "is_valid")
        assert hasattr(result, "errors")
        assert hasattr(result, "warnings")
        assert hasattr(result, "parsed_string")
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)


class TestHedToolsErrorParsing:
    """Tests for error data parsing."""

    def test_parse_empty_error(self):
        """Empty error data should produce no issues."""
        validator = HedToolsAPIValidator()
        errors, warnings = validator._parse_error_data("")
        assert len(errors) == 0
        assert len(warnings) == 0

    def test_parse_string_error(self):
        """String error data should be parsed into issues."""
        validator = HedToolsAPIValidator()
        errors, warnings = validator._parse_error_data("TAG_INVALID: 'FakeTag' is not a valid tag")
        assert len(errors) == 1
        assert errors[0].code == "TAG_INVALID"

    def test_parse_list_error(self):
        """List error data should be parsed into issues."""
        validator = HedToolsAPIValidator()
        errors, warnings = validator._parse_error_data(
            ["TAG_INVALID: 'FakeTag' is not valid", "VALUE_INVALID: bad value"]
        )
        assert len(errors) == 2

    def test_parse_multiline_error(self):
        """Multi-line string error data should produce multiple issues."""
        validator = HedToolsAPIValidator()
        errors, warnings = validator._parse_error_data(
            "TAG_INVALID: 'A' is invalid\nTAG_INVALID: 'B' is invalid"
        )
        assert len(errors) == 2

    def test_parse_response_success(self):
        """Successful response should return valid result."""
        validator = HedToolsAPIValidator()
        result = validator._parse_response({"results": {"msg_category": "success"}})
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_parse_response_error(self):
        """Error response should return invalid result."""
        validator = HedToolsAPIValidator()
        result = validator._parse_response(
            {
                "results": {
                    "msg_category": "warning",
                    "data": "TAG_INVALID: 'BadTag' not valid",
                }
            }
        )
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_parse_error_data_unexpected_type(self):
        """Non-str, non-list input should produce a PARSE_ERROR."""
        validator = HedToolsAPIValidator()
        errors, warnings = validator._parse_error_data({"key": "value"})
        assert len(errors) == 1
        assert errors[0].code == "PARSE_ERROR"
        assert len(warnings) == 0

    def test_parse_error_data_warning_codes(self):
        """TAG_EXTENDED should be classified as warning, not error."""
        validator = HedToolsAPIValidator()
        errors, warnings = validator._parse_error_data("TAG_EXTENDED: 'Animal/Marmoset' extended")
        assert len(warnings) == 1
        assert warnings[0].code == "TAG_EXTENDED"
        assert len(errors) == 0

    def test_parse_error_data_mixed_codes(self):
        """Mix of error and warning codes should be correctly classified."""
        validator = HedToolsAPIValidator()
        errors, warnings = validator._parse_error_data(
            [
                "TAG_INVALID: 'BadTag' not valid",
                "TAG_EXTENDED: 'Animal/Cat' extended",
            ]
        )
        assert len(errors) == 1
        assert errors[0].code == "TAG_INVALID"
        assert len(warnings) == 1
        assert warnings[0].code == "TAG_EXTENDED"

    def test_parse_error_data_unrecognized_format(self):
        """Lines without CODE: prefix should get VALIDATION_ERROR code."""
        validator = HedToolsAPIValidator()
        errors, warnings = validator._parse_error_data("some unknown error format")
        assert len(errors) == 1
        assert errors[0].code == "VALIDATION_ERROR"
        assert errors[0].message == "some unknown error format"
