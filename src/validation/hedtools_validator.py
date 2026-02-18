"""HED validation via the hedtools.org REST API.

Provides remote validation without requiring local HED tools installation.
Uses the hedtools.org services endpoint with CSRF token authentication.
"""

from __future__ import annotations

import logging
import re
import time

import httpx

from src.validation.hed_validator import ValidationIssue, ValidationResult

logger = logging.getLogger(__name__)

# Default hedtools.org base URL
HEDTOOLS_BASE_URL = "https://hedtools.org/hed"

# Session cache TTL in seconds (CSRF tokens expire; refresh periodically)
_SESSION_TTL = 300  # 5 minutes


class HedToolsAPIValidator:
    """Validates HED strings using the hedtools.org REST API.

    This validator sends HED strings to hedtools.org for server-side validation,
    avoiding the need for local JavaScript or Python HED tools.

    Session info (cookie + CSRF token) is cached and reused within the TTL
    to avoid redundant requests.
    """

    def __init__(
        self,
        base_url: str = HEDTOOLS_BASE_URL,
        schema_version: str = "8.4.0",
        timeout: float = 30.0,
    ) -> None:
        """Initialize the hedtools.org API validator.

        Args:
            base_url: Base URL for hedtools.org (without trailing slash)
            schema_version: HED schema version to validate against
            timeout: HTTP request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.schema_version = schema_version
        self.timeout = timeout
        self._session_cookie: str | None = None
        self._csrf_token: str | None = None
        self._session_timestamp: float = 0.0

    def _get_session_info(self) -> tuple[str, str]:
        """Obtain session cookie and CSRF token from hedtools.org.

        Returns:
            Tuple of (session_cookie, csrf_token)

        Raises:
            httpx.HTTPError: If the request to hedtools.org fails
            ValueError: If cookie or CSRF token cannot be extracted
        """
        # Return cached session if still valid
        if (
            self._session_cookie
            and self._csrf_token
            and (time.monotonic() - self._session_timestamp) < _SESSION_TTL
        ):
            return self._session_cookie, self._csrf_token

        csrf_url = f"{self.base_url}/services"
        response = httpx.get(csrf_url, timeout=self.timeout, follow_redirects=True)
        response.raise_for_status()

        # Extract session cookie
        cookie = response.cookies.get("session")
        if not cookie:
            set_cookie = response.headers.get("set-cookie", "")
            cookie_match = re.search(r"session=([^;]+)", set_cookie)
            cookie = cookie_match.group(1) if cookie_match else None

        if not cookie:
            raise ValueError("Failed to obtain session cookie from hedtools.org")

        # Extract CSRF token from HTML form
        html = response.text
        csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
        if not csrf_match:
            raise ValueError("Failed to extract CSRF token from hedtools.org response")

        csrf_token = csrf_match.group(1)

        # Cache for reuse
        self._session_cookie = cookie
        self._csrf_token = csrf_token
        self._session_timestamp = time.monotonic()

        return cookie, csrf_token

    def validate(self, hed_string: str) -> ValidationResult:
        """Validate a HED string via the hedtools.org REST API.

        Args:
            hed_string: HED annotation string to validate

        Returns:
            ValidationResult with errors and warnings
        """
        url = f"{self.base_url}/services_submit"

        try:
            cookie, csrf_token = self._get_session_info()

            payload = {
                "service": "strings_validate",
                "schema_version": self.schema_version,
                "string_list": [hed_string],
                "check_for_warnings": True,
            }

            headers = {
                "X-CSRFToken": csrf_token,
                "Cookie": f"session={cookie}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            response = httpx.post(url, json=payload, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()

            return self._parse_response(result)

        except httpx.TimeoutException:
            return ValidationResult(
                is_valid=False,
                errors=[
                    ValidationIssue(
                        code="TIMEOUT",
                        level="error",
                        message="hedtools.org validation timed out",
                    )
                ],
                warnings=[],
            )
        except httpx.HTTPError as e:
            logger.warning("hedtools.org HTTP error: %s", e)
            return ValidationResult(
                is_valid=False,
                errors=[
                    ValidationIssue(
                        code="HTTP_ERROR",
                        level="error",
                        message=f"hedtools.org request failed: {e}",
                    )
                ],
                warnings=[],
            )
        except ValueError as e:
            logger.warning("hedtools.org session error: %s", e)
            # Invalidate cached session on auth errors
            self._session_cookie = None
            self._csrf_token = None
            return ValidationResult(
                is_valid=False,
                errors=[
                    ValidationIssue(
                        code="SESSION_ERROR",
                        level="error",
                        message=f"hedtools.org authentication failed: {e}",
                    )
                ],
                warnings=[],
            )

    def _parse_response(self, result: dict) -> ValidationResult:
        """Parse the hedtools.org API response into a ValidationResult.

        Args:
            result: Raw JSON response from hedtools.org

        Returns:
            Structured ValidationResult
        """
        results = result.get("results", {})
        msg_category = results.get("msg_category", "error")

        if msg_category == "success":
            return ValidationResult(
                is_valid=True,
                errors=[],
                warnings=[],
                parsed_string=None,
            )

        # Parse error/warning text from the data field
        error_data = results.get("data", "Unknown validation error")
        errors, warnings = self._parse_error_data(error_data)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _parse_error_data(
        self, error_data: str | list
    ) -> tuple[list[ValidationIssue], list[ValidationIssue]]:
        """Parse error data from hedtools.org into ValidationIssue lists.

        The hedtools.org API returns errors as either a string or list.
        Each line typically contains the error code and message.

        Args:
            error_data: Raw error data from the API response

        Returns:
            Tuple of (errors, warnings)
        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []

        if isinstance(error_data, list):
            lines = error_data
        elif isinstance(error_data, str):
            lines = [line.strip() for line in error_data.split("\n") if line.strip()]
        else:
            errors.append(
                ValidationIssue(
                    code="PARSE_ERROR",
                    level="error",
                    message=str(error_data),
                )
            )
            return errors, warnings

        for line in lines:
            line_str = str(line).strip()
            if not line_str:
                continue

            # Try to extract error code from line (e.g., "TAG_INVALID: ...")
            code_match = re.match(r"([A-Z_]+):\s*(.*)", line_str)
            if code_match:
                code = code_match.group(1)
                message = code_match.group(2) or line_str
            else:
                code = "VALIDATION_ERROR"
                message = line_str

            # Classify as warning or error based on code
            warning_codes = {"TAG_EXTENDED", "SUGGESTION"}
            level = "warning" if code in warning_codes else "error"

            issue = ValidationIssue(
                code=code,
                level=level,
                message=message,
            )

            if level == "warning":
                warnings.append(issue)
            else:
                errors.append(issue)

        return errors, warnings


def is_hedtools_available(
    base_url: str = HEDTOOLS_BASE_URL,
    timeout: float = 5.0,
) -> bool:
    """Check if the hedtools.org API is reachable.

    Args:
        base_url: Base URL for hedtools.org
        timeout: Connection timeout in seconds

    Returns:
        True if hedtools.org is reachable
    """
    try:
        response = httpx.get(
            f"{base_url}/services",
            timeout=timeout,
            follow_redirects=True,
        )
        return response.status_code == 200
    except httpx.HTTPError:
        return False
