"""Validation Agent for HED annotation validation.

This agent validates HED annotation strings using HED validation tools
and provides detailed feedback for corrections.
"""

from pathlib import Path

from src.agents.state import HedAnnotationState
from src.utils.error_remediation import get_remediator
from src.utils.schema_loader import HedSchemaLoader
from src.validation.hed_validator import HedJavaScriptValidator, HedPythonValidator


class ValidationAgent:
    """Agent that validates HED annotations using HED validation tools.

    Supports both JavaScript validator (detailed feedback) and Python validator (fallback).
    """

    def __init__(
        self,
        schema_loader: HedSchemaLoader,
        use_javascript: bool = True,
        validator_path: Path | None = None,
        tests_json_path: Path | str | None = None,
    ) -> None:
        """Initialize the validation agent.

        Args:
            schema_loader: HED schema loader
            use_javascript: Whether to use JavaScript validator (more detailed)
            validator_path: Path to hed-javascript repository (required if use_javascript=True)
            tests_json_path: Optional path to javascriptTests.json for error remediation
        """
        self.schema_loader = schema_loader
        self.use_javascript = use_javascript
        self.error_remediator = get_remediator(tests_json_path)

        if use_javascript:
            if validator_path is None:
                raise ValueError("validator_path required when use_javascript=True")
            self.js_validator = HedJavaScriptValidator(validator_path)
            self.py_validator = None
        else:
            self.js_validator = None
            self.py_validator = None  # Created per-schema

    async def validate(self, state: HedAnnotationState) -> dict:
        """Validate the current HED annotation.

        Args:
            state: Current annotation workflow state

        Returns:
            State update with validation results
        """
        annotation = state["current_annotation"]
        schema_version = state["schema_version"]

        # Validate using appropriate validator
        if self.use_javascript and self.js_validator:
            result = self.js_validator.validate(annotation)
        else:
            # Use Python validator
            schema = self.schema_loader.load_schema(schema_version)
            if self.py_validator is None:
                self.py_validator = HedPythonValidator(schema)
            result = self.py_validator.validate(annotation)

        # Extract error and warning messages (raw - for user display)
        raw_errors = [f"[{e.code}] {e.message}" for e in result.errors]
        raw_warnings = [f"[{w.code}] {w.message}" for w in result.warnings]

        # Augment with remediation guidance (for LLM feedback loop only)
        augmented_errors, augmented_warnings = self.error_remediator.augment_validation_errors(
            raw_errors, raw_warnings
        )

        # Determine validation status
        validation_attempts = state["validation_attempts"] + 1
        max_attempts = state["max_validation_attempts"]

        # IMPORTANT: Safeguard to ensure is_valid is only True when there are NO errors
        # This prevents discrepancies between is_valid flag and actual validation_errors
        is_valid = result.is_valid and len(raw_errors) == 0

        if is_valid:
            validation_status = "valid"
        elif validation_attempts >= max_attempts:
            validation_status = "max_attempts_reached"
        else:
            validation_status = "invalid"

        # Return both raw (for users) and augmented (for LLM) errors/warnings
        return {
            "validation_status": validation_status,
            "validation_errors": raw_errors,  # Raw errors for user display
            "validation_warnings": raw_warnings,  # Raw warnings for user display
            "validation_errors_augmented": augmented_errors,  # For LLM feedback
            "validation_warnings_augmented": augmented_warnings,  # For LLM feedback
            "validation_attempts": validation_attempts,
            "is_valid": is_valid,
        }
