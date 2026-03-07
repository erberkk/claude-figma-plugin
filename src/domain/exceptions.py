
from __future__ import annotations

class AppError(Exception):
    """Base application error."""

    def __init__(self, message: str, *, code: str = "INTERNAL_ERROR", status: int = 500) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status

class ValidationError(AppError):
    """Raised when input or Claude output fails validation."""

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message, code="VALIDATION_ERROR", status=422)
        self.details = details or {}

class ClaudeError(AppError):
    """Raised when the Claude API call fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="CLAUDE_ERROR", status=502)

class ClaudeTimeoutError(AppError):
    """Raised when Claude request times out."""

    def __init__(self) -> None:
        super().__init__("Claude request timed out", code="TIMEOUT", status=504)

class AuthError(AppError):
    """Raised on authentication failure."""

    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message, code="AUTH_ERROR", status=401)

class InputTooLargeError(AppError):
    """Raised when request body exceeds the configured limit."""

    def __init__(self, max_size: int) -> None:
        super().__init__(
            f"Request body exceeds maximum size of {max_size} bytes",
            code="INPUT_TOO_LARGE",
            status=413,
        )

class PromptInjectionError(AppError):
    """Raised when prompt injection patterns are detected."""

    def __init__(self) -> None:
        super().__init__(
            "Input contains disallowed patterns",
            code="PROMPT_INJECTION",
            status=400,
        )
