"""
Error handling utilities and exception handlers for ZapStream Backend.

Provides consistent error response format with proper logging and request correlation.
"""

from typing import Dict, Any
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .models import ErrorResponse
from .logging import setup_logging

logger = setup_logging()


class ZapStreamException(Exception):
    """Base exception for ZapStream application errors."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        details: Dict[str, Any] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(ZapStreamException):
    """Exception for validation errors."""

    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=400,
            details=details
        )


class AuthenticationException(ZapStreamException):
    """Exception for authentication errors."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            code="AUTHENTICATION_ERROR",
            message=message,
            status_code=401
        )


class RateLimitException(ZapStreamException):
    """Exception for rate limit exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        details = {}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message=message,
            status_code=429,
            details=details
        )


class ConflictException(ZapStreamException):
    """Exception for conflicts (e.g., idempotency key already used)."""

    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(
            code="CONFLICT",
            message=message,
            status_code=409,
            details=details
        )


class NotFoundException(ZapStreamException):
    """Exception for resource not found errors."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(
            code="NOT_FOUND",
            message=message,
            status_code=404
        )


def create_error_response(
    code: str,
    message: str,
    request_id: str = None,
    details: Dict[str, Any] = None
) -> JSONResponse:
    """Create a standardized error response."""

    error_content = {
        "code": code,
        "message": message
    }

    if request_id:
        error_content["requestId"] = request_id

    if details:
        error_content.update(details)

    return JSONResponse(
        status_code=get_status_code_for_error(code),
        content=ErrorResponse(error=error_content).model_dump()
    )


def get_status_code_for_error(code: str) -> int:
    """Map error codes to HTTP status codes."""

    status_map = {
        "VALIDATION_ERROR": 400,
        "AUTHENTICATION_ERROR": 401,
        "FORBIDDEN": 403,
        "NOT_FOUND": 404,
        "CONFLICT": 409,
        "RATE_LIMIT_EXCEEDED": 429,
        "INTERNAL_ERROR": 500,
        "SERVICE_UNAVAILABLE": 503,
    }

    return status_map.get(code, 500)


def get_request_id(request: Request) -> str:
    """Extract request ID from request state or generate one."""
    return getattr(request.state, 'request_id', None)


def log_error(
    code: str,
    message: str,
    request: Request = None,
    details: Dict[str, Any] = None
):
    """Log error with context."""

    extra = {}

    if request:
        extra['request_id'] = get_request_id(request)
        extra['path'] = request.url.path
        extra['method'] = request.method

        if hasattr(request.state, 'tenant_id'):
            extra['tenant_id'] = request.state.tenant_id

    if details:
        extra['details'] = details

    logger.error(f"{code}: {message}", extra=extra)


# Exception Handlers
async def zapstream_exception_handler(request: Request, exc: ZapStreamException):
    """Handle custom ZapStream exceptions."""

    request_id = get_request_id(request)

    log_error(
        code=exc.code,
        message=exc.message,
        request=request,
        details=exc.details
    )

    return create_error_response(
        code=exc.code,
        message=exc.message,
        request_id=request_id,
        details=exc.details if exc.details else None
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTPExceptions."""

    request_id = get_request_id(request)

    # Convert HTTP status to error code
    error_code = {
        400: "VALIDATION_ERROR",
        401: "AUTHENTICATION_ERROR",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_ERROR",
        503: "SERVICE_UNAVAILABLE",
    }.get(exc.status_code, "HTTP_ERROR")

    log_error(
        code=error_code,
        message=str(exc.detail),
        request=request
    )

    return create_error_response(
        code=error_code,
        message=str(exc.detail),
        request_id=request_id
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""

    request_id = get_request_id(request)

    # Format validation errors for response
    validation_details = []
    for error in exc.errors():
        field_path = "->".join(str(loc) for loc in error['loc'])
        validation_details.append({
            "field": field_path,
            "message": error['msg'],
            "type": error['type']
        })

    message = "Request validation failed"
    details = {"validation_errors": validation_details}

    log_error(
        code="VALIDATION_ERROR",
        message=message,
        request=request,
        details=details
    )

    return create_error_response(
        code="VALIDATION_ERROR",
        message=message,
        request_id=request_id,
        details=details
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle any uncaught exceptions."""

    request_id = get_request_id(request)

    # Don't expose internal error details in production
    message = "An unexpected error occurred"

    log_error(
        code="INTERNAL_ERROR",
        message=f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        request=request,
        details={"exception_type": type(exc).__name__}
    )

    return create_error_response(
        code="INTERNAL_ERROR",
        message=message,
        request_id=request_id
    )