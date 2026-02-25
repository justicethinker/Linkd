"""Custom exceptions and error handling."""

from fastapi import HTTPException, status
from typing import Any, Optional


class LinkdException(Exception):
    """Base exception for Linkd application."""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[dict] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class ValidationError(LinkdException):
    """Validation error."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY, details)


class NotFoundError(LinkdException):
    """Resource not found error."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, status.HTTP_404_NOT_FOUND, details)


class UnauthorizedError(LinkdException):
    """Unauthorized access error."""
    
    def __init__(self, message: str = "Unauthorized", details: Optional[dict] = None):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED, details)


class ForbiddenError(LinkdException):
    """Forbidden access error."""
    
    def __init__(self, message: str = "Forbidden", details: Optional[dict] = None):
        super().__init__(message, status.HTTP_403_FORBIDDEN, details)


class ExternalServiceError(LinkdException):
    """External service error (e.g., Deepgram, Gemini, etc.)."""
    
    def __init__(self, service: str, message: str, details: Optional[dict] = None):
        full_message = f"{service} error: {message}"
        super().__init__(full_message, status.HTTP_502_BAD_GATEWAY, details)


class ResourceQuotaExceededError(LinkdException):
    """Resource quota exceeded error."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, status.HTTP_429_TOO_MANY_REQUESTS, details)


class FileSizeError(ValidationError):
    """File size exceeds limit."""
    
    def __init__(self, max_size_mb: int, actual_size_mb: float):
        message = f"File size ({actual_size_mb:.1f}MB) exceeds maximum ({max_size_mb}MB)"
        super().__init__(message, {"max_size_mb": max_size_mb, "actual_size_mb": actual_size_mb})


def to_http_exception(exc: LinkdException) -> HTTPException:
    """Convert LinkdException to HTTPException."""
    return HTTPException(
        status_code=exc.status_code,
        detail={
            "error": exc.message,
            "details": exc.details,
        },
    )
