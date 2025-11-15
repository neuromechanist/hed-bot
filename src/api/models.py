"""Pydantic models for API requests and responses."""

from pydantic import BaseModel, Field


class AnnotationRequest(BaseModel):
    """Request model for HED annotation generation.

    Attributes:
        description: Natural language event description to annotate
        schema_version: HED schema version to use
        max_validation_attempts: Maximum validation retry attempts
    """

    description: str = Field(
        ...,
        description="Natural language event description",
        min_length=1,
        examples=["A red circle appears on the left side of the screen"],
    )
    schema_version: str = Field(
        default="8.3.0",
        description="HED schema version",
        examples=["8.3.0", "8.4.0"],
    )
    max_validation_attempts: int = Field(
        default=5,
        description="Maximum validation retry attempts",
        ge=1,
        le=10,
    )


class AnnotationResponse(BaseModel):
    """Response model for HED annotation generation.

    Attributes:
        annotation: Generated HED annotation string
        is_valid: Whether the annotation passed validation
        is_faithful: Whether the annotation is faithful to description
        is_complete: Whether the annotation is complete
        validation_attempts: Number of validation attempts made
        validation_errors: List of validation errors (if any)
        validation_warnings: List of validation warnings (if any)
        evaluation_feedback: Evaluation agent feedback
        assessment_feedback: Assessment agent feedback
        status: Overall workflow status
    """

    annotation: str = Field(..., description="Generated HED annotation string")
    is_valid: bool = Field(..., description="Validation status")
    is_faithful: bool = Field(..., description="Faithfulness to original description")
    is_complete: bool = Field(..., description="Completeness status")
    validation_attempts: int = Field(..., description="Number of validation attempts")
    validation_errors: list[str] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)
    evaluation_feedback: str = Field(default="")
    assessment_feedback: str = Field(default="")
    status: str = Field(..., description="Workflow status", examples=["success", "failed"])


class ValidationRequest(BaseModel):
    """Request model for HED validation only.

    Attributes:
        hed_string: HED annotation string to validate
        schema_version: HED schema version to use
    """

    hed_string: str = Field(
        ...,
        description="HED annotation string",
        min_length=1,
    )
    schema_version: str = Field(
        default="8.3.0",
        description="HED schema version",
    )


class ValidationResponse(BaseModel):
    """Response model for HED validation.

    Attributes:
        is_valid: Whether the HED string is valid
        errors: List of validation errors
        warnings: List of validation warnings
        parsed_string: Normalized HED string (if valid)
    """

    is_valid: bool = Field(..., description="Validation status")
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    parsed_string: str | None = Field(default=None)


class HealthResponse(BaseModel):
    """Response model for health check.

    Attributes:
        status: Service status
        version: API version
        llm_available: Whether LLM is available
        validator_available: Whether HED validator is available
    """

    status: str = Field(..., examples=["healthy", "degraded"])
    version: str = Field(..., examples=["0.1.0"])
    llm_available: bool
    validator_available: bool
