"""
Custom exceptions for Viewpoint Prism application.
Provides standardized error handling across all modules.
"""

from fastapi import HTTPException, status
from typing import Optional, Any


class AppException(HTTPException):
    """Base application exception."""

    def __init__(
        self,
        detail: str = "An error occurred",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        headers: Optional[dict] = None,
    ):
        super().__init__(
            status_code=status_code,
            detail=detail,
            headers=headers,
        )
        self.logger_name = "app"


class NotFoundException(AppException):
    """Resource not found exception."""

    def __init__(
        self,
        resource: str = "Resource",
        resource_id: Optional[str] = None,
        detail: Optional[str] = None,
    ):
        if detail is None:
            if resource_id:
                detail = f"{resource} with id '{resource_id}' not found"
            else:
                detail = f"{resource} not found"
        super().__init__(
            detail=detail,
            status_code=status.HTTP_404_NOT_FOUND,
        )
        self.resource = resource
        self.resource_id = resource_id


class ValidationException(AppException):
    """Validation error exception."""

    def __init__(self, detail: str = "Validation failed"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class BadRequestException(AppException):
    """Bad request exception."""

    def __init__(self, detail: str = "Invalid request"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class UnauthorizedException(AppException):
    """Unauthorized access exception."""

    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenException(AppException):
    """Forbidden access exception."""

    def __init__(self, detail: str = "Access forbidden"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class ConflictException(AppException):
    """Resource conflict exception."""

    def __init__(self, detail: str = "Resource conflict"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_409_CONFLICT,
        )


class InternalException(AppException):
    """Internal server error exception."""

    def __init__(self, detail: str = "Internal server error"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class ServiceUnavailableException(AppException):
    """Service temporarily unavailable."""

    def __init__(self, detail: str = "Service temporarily unavailable"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class TaskException(AppException):
    """Task-related exception with status tracking."""

    def __init__(
        self,
        task_id: str,
        status: str,
        detail: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ):
        super().__init__(detail=detail, status_code=status_code)
        self.task_id = task_id
        self.task_status = status


def handle_exception(exc: Exception) -> AppException:
    """Convert unknown exception to AppException."""
    if isinstance(exc, AppException):
        return exc

    exc_type = type(exc).__name__
    exc_message = str(exc)

    if "not found" in exc_message.lower():
        return NotFoundException(detail=exc_message)
    elif "validation" in exc_message.lower():
        return ValidationException(detail=exc_message)
    elif "unique" in exc_message.lower() or "duplicate" in exc_message.lower():
        return ConflictException(detail=exc_message)
    else:
        logger_name = "app"
        logging.getLogger(logger_name).error(
            f"Unhandled exception: {exc_type}: {exc_message}"
        )
        return InternalException(detail=f"{exc_type}: {exc_message}")
