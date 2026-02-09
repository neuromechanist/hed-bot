# HED Validation Tools

## Overview
HEDit uses a dual-validator approach for comprehensive HED string validation. The validation agent (`src/validation/hed_validator.py`) tries the JavaScript validator first, falling back to Python.

## Validators

### JavaScript Validator (`HedJavaScriptValidator`)
- **Preferred** for production use
- Runs via Node.js subprocess calling `hed-javascript` package
- More detailed error categorization
- Reclassifies certain warnings that are actually errors
- Requires: Node.js + `hed-javascript` installation

### Python Validator (`HedPythonValidator`)
- **Fallback** when JavaScript not available
- Uses `hedtools` Python package
- Pure Python, no external dependencies
- Less detailed error messages

### hedtools.org REST API (OSA approach)
- Used by OSA's HED assistant for real-time validation
- Endpoint: `https://hedtools.org/hed/services_submit`
- Requires CSRF token + session cookie
- Service: `strings_validate`
- No local installation needed
- Better for chat/assistant use cases

## Validation Result Structure

```python
@dataclass
class ValidationIssue:
    code: str           # e.g., "TAG_INVALID"
    level: str          # "error" | "warning"
    message: str        # Human-readable description
    tag: str | None     # Problem tag
    context: dict | None

@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[ValidationIssue]
    warnings: list[ValidationIssue]
    parsed_string: str | None  # Normalized string if valid
```

## Error Augmentation
`src/utils/error_remediation.py` enhances validation errors for LLM feedback:
- Explains WHY each error occurred
- Provides specific fixes
- Uses closest-match algorithm for tag suggestions
- Feeds augmented errors back to annotation agent for correction

## Integration in Workflow
1. Annotation agent generates HED string
2. Validation agent validates (JS or Python)
3. If invalid: errors augmented, fed back via feedback summarizer
4. Annotation agent corrects based on augmented feedback
5. Loop continues up to `max_validation_attempts` (default: 5)

## External Dependencies
- **hed-javascript**: `/Users/yahya/Documents/git/HED/hed-javascript`
- **hed-python**: `hedtools` package (pip installable)
- **hedtools.org**: REST API for remote validation
