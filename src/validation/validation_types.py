"""Shared types for HED validation.

Contains dataclasses used across all validator backends to avoid
circular imports between validator modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class ValidationIssue:
    """Represents a single validation issue (error or warning).

    Attributes:
        code: Issue code (e.g., 'TAG_INVALID')
        level: Severity level ('error' or 'warning')
        message: Human-readable error message
        tag: The problematic tag (if applicable)
        context: Additional context information
    """

    code: str
    level: Literal["error", "warning"]
    message: str
    tag: str | None = None
    context: dict | None = None


@dataclass
class ValidationResult:
    """Result of HED string validation.

    Attributes:
        is_valid: Whether the HED string is valid
        errors: List of error issues
        warnings: List of warning issues
        parsed_string: Successfully parsed HED string (if valid)
    """

    is_valid: bool
    errors: list[ValidationIssue]
    warnings: list[ValidationIssue]
    parsed_string: str | None = None
