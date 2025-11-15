"""Tests for HED validation."""

import pytest

from src.utils.schema_loader import HedSchemaLoader
from src.validation.hed_validator import HedPythonValidator


@pytest.fixture
def validator():
    """Create a HED Python validator."""
    loader = HedSchemaLoader()
    schema = loader.load_schema("8.3.0")
    return HedPythonValidator(schema)


def test_validate_valid_string(validator):
    """Test validation of a valid HED string."""
    result = validator.validate("Sensory-event, Visual-presentation")

    assert result.is_valid is True
    assert len(result.errors) == 0


def test_validate_invalid_tag(validator):
    """Test validation of invalid tag."""
    result = validator.validate("Invalid-nonexistent-tag")

    assert result.is_valid is False
    assert len(result.errors) > 0


def test_validate_with_grouping(validator):
    """Test validation of properly grouped tags."""
    result = validator.validate("Sensory-event, (Red, Circle)")

    assert result.is_valid is True or len(result.errors) == 0


def test_validation_result_structure(validator):
    """Test structure of validation result."""
    result = validator.validate("Sensory-event")

    assert hasattr(result, "is_valid")
    assert hasattr(result, "errors")
    assert hasattr(result, "warnings")
    assert hasattr(result, "parsed_string")
    assert isinstance(result.errors, list)
    assert isinstance(result.warnings, list)
