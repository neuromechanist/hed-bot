"""Tests for LangGraph state."""

from src.agents.state import create_initial_state


def test_create_initial_state():
    """Test creating initial annotation state."""
    description = "A red circle appears on screen"
    state = create_initial_state(description)

    assert state["input_description"] == description
    assert state["current_annotation"] == ""
    assert state["validation_status"] == "pending"
    assert state["validation_attempts"] == 0
    assert state["is_valid"] is False
    assert state["is_faithful"] is False
    assert state["is_complete"] is False
    assert state["max_validation_attempts"] == 5
    assert state["schema_version"] == "8.3.0"


def test_create_initial_state_custom_params():
    """Test creating initial state with custom parameters."""
    description = "Test event"
    state = create_initial_state(
        description,
        schema_version="8.4.0",
        max_validation_attempts=3,
    )

    assert state["schema_version"] == "8.4.0"
    assert state["max_validation_attempts"] == 3
