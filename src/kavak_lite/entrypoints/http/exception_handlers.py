"""FastAPI exception handlers for domain errors.

Translates domain errors to appropriate HTTP responses with structured error format.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from kavak_lite.domain.errors import DomainError

logger = logging.getLogger(__name__)


async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
    """Handle all domain errors with automatic HTTP status code mapping.

    Maps domain errors to appropriate HTTP status codes:
    - VALIDATION_ERROR → 422 Unprocessable Entity
    - NOT_FOUND → 404 Not Found
    - CONFLICT → 409 Conflict
    - UNAUTHORIZED → 401 Unauthorized
    - FORBIDDEN → 403 Forbidden
    - INTERNAL_ERROR → 500 Internal Server Error
    - Other → 400 Bad Request

    Args:
        request: FastAPI request object
        exc: Domain error to handle

    Returns:
        JSON response with structured error format
    """
    error_dict = exc.to_dict()

    # Map error codes to HTTP status codes
    status_code_map: dict[str, int] = {
        "VALIDATION_ERROR": 422,  # HTTP_422_UNPROCESSABLE_CONTENT
        "NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "CONFLICT": status.HTTP_409_CONFLICT,
        "UNAUTHORIZED": status.HTTP_401_UNAUTHORIZED,
        "FORBIDDEN": status.HTTP_403_FORBIDDEN,
        "INTERNAL_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    }

    status_code = status_code_map.get(exc.error_code, status.HTTP_400_BAD_REQUEST)

    # Log errors (except expected validation errors)
    if status_code >= 500:
        logger.error(
            "Domain error occurred",
            extra={
                "error_code": exc.error_code,
                "message": exc.message,
                "context": exc.context,
                "path": request.url.path,
                "method": request.method,
            },
        )
    elif status_code >= 400:
        logger.info(
            "Client error",
            extra={
                "error_code": exc.error_code,
                "message": exc.message,
                "path": request.url.path,
                "method": request.method,
            },
        )

    # Build structured response
    response_content: dict[str, Any] = {
        "detail": error_dict.get("message", str(exc)),
        "code": error_dict.get("code", exc.error_code),
    }

    # Add field-level errors if present (for ValidationError)
    if "errors" in error_dict:
        response_content["errors"] = error_dict["errors"]

    return JSONResponse(status_code=status_code, content=response_content)


async def handle_request_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle FastAPI/Pydantic validation errors.

    These are type errors, format errors, constraint violations at the HTTP layer.

    Examples:
        - price_min=abc (not a valid format)
        - limit=500 (exceeds max constraint)
        - Missing required field

    Args:
        request: FastAPI request object
        exc: Pydantic validation error

    Returns:
        JSON response with 422 status and structured errors
    """
    errors = []

    for error in exc.errors():
        # Extract field path from error location
        # Filter out 'body' and 'query' prefixes
        field_path = ".".join(str(loc) for loc in error["loc"] if loc not in ("body", "query"))

        errors.append(
            {
                "field": field_path,
                "message": error["msg"],
                "code": error["type"],
            }
        )

    logger.info(
        "Request validation error",
        extra={
            "errors": errors,
            "path": request.url.path,
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=422,  # HTTP_422_UNPROCESSABLE_CONTENT
        content={
            "detail": "Invalid request parameters",
            "code": "VALIDATION_ERROR",
            "errors": errors,
        },
    )


async def handle_value_error(request: Request, exc: ValueError) -> JSONResponse:
    """Handle ValueError from domain logic or mappers.

    Often raised during type conversions (e.g., Decimal parsing).

    Args:
        request: FastAPI request object
        exc: ValueError exception

    Returns:
        JSON response with 422 status
    """
    logger.info(
        "Value error",
        extra={
            "message": str(exc),
            "path": request.url.path,
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=422,  # HTTP_422_UNPROCESSABLE_CONTENT
        content={
            "detail": str(exc),
            "code": "INVALID_VALUE",
        },
    )


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unexpected errors.

    These should be rare and indicate bugs or infrastructure issues.
    Always logged with full traceback for investigation.

    Args:
        request: FastAPI request object
        exc: Unexpected exception

    Returns:
        JSON response with 500 status and generic error message
    """
    logger.error(
        "Unexpected error occurred",
        exc_info=exc,
        extra={
            "error_type": type(exc).__name__,
            "message": str(exc),
            "path": request.url.path,
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected error occurred",
            "code": "INTERNAL_ERROR",
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with FastAPI app.

    This should be called once during app initialization.

    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(DomainError, handle_domain_error)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, handle_request_validation_error)  # type: ignore[arg-type]
    app.add_exception_handler(ValueError, handle_value_error)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, handle_unexpected_error)

    logger.info("Exception handlers registered successfully")
