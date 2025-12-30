"""Domain error classes.

Protocol-agnostic errors that represent business failures.
These errors are translated to appropriate formats (HTTP, GraphQL, gRPC) by protocol adapters.
"""

from typing import Any


class DomainError(Exception):
    """Base class for all domain errors.

    Protocol-agnostic. Contains business error information that
    can be translated to HTTP, GraphQL, or gRPC formats.
    """

    # Default error code (can be used as i18n key)
    error_code: str = "DOMAIN_ERROR"

    def __init__(self, message: str, **context: Any) -> None:
        """Create a domain error.

        Args:
            message: Human-readable error message (default locale)
            **context: Additional context for error (e.g., field names, values)
                      Can be used for i18n interpolation in the future
        """
        self.message = message
        self.context = context
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert to structured format for protocol translation."""
        return {
            "message": self.message,
            "code": self.error_code,
            **self.context,
        }


class ValidationError(DomainError):
    """Business rule validation error.

    Used for domain invariant violations and cross-field validation.

    Examples:
        - price_min > price_max
        - year_min > year_max
        - Invalid state transitions
        - Business constraint violations

    Protocol mappings:
        - REST: 422 Unprocessable Entity
        - GraphQL: 200 OK with errors array
        - gRPC: INVALID_ARGUMENT (3)
    """

    error_code: str = "VALIDATION_ERROR"

    def __init__(
        self,
        message: str | None = None,
        errors: list[dict[str, str]] | None = None,
        **context: Any,
    ) -> None:
        """Create a validation error.

        Args:
            message: Overall validation error message (optional if errors provided)
            errors: List of field-specific errors, each with 'field' and 'message'
                   Example: [{"field": "price_min", "message": "Must be positive"}]
            **context: Additional context
        """
        self.errors: list[dict[str, str]] | None
        if errors:
            self.errors = errors
            msg = message or "Validation failed"
        else:
            self.errors = None
            msg = message or "Validation error"

        super().__init__(msg, **context)

    def to_dict(self) -> dict[str, Any]:
        """Convert to structured format."""
        if self.errors:
            return {
                "message": self.message,
                "code": self.error_code,
                "errors": self.errors,
                **self.context,
            }
        return super().to_dict()


class NotFoundError(DomainError):
    """Resource not found.

    Examples:
        - Car with ID not found
        - User not found
        - Catalog entry doesn't exist

    Protocol mappings:
        - REST: 404 Not Found
        - GraphQL: 200 OK with errors array (or null field)
        - gRPC: NOT_FOUND (5)
    """

    error_code: str = "NOT_FOUND"

    def __init__(self, resource: str, identifier: str | None = None, **context: Any) -> None:
        """Create a not found error.

        Args:
            resource: Type of resource (e.g., "Car", "User")
            identifier: Resource identifier (e.g., UUID, ID)
            **context: Additional context
        """
        if identifier:
            message = f"{resource} with identifier '{identifier}' not found"
        else:
            message = f"{resource} not found"

        super().__init__(message, resource=resource, identifier=identifier, **context)


class ConflictError(DomainError):
    """Business constraint conflict.

    Examples:
        - Duplicate resource (e.g., car VIN already exists)
        - Concurrent modification conflict
        - State transition not allowed

    Protocol mappings:
        - REST: 409 Conflict
        - GraphQL: 200 OK with errors array
        - gRPC: ALREADY_EXISTS (6) or FAILED_PRECONDITION (9)
    """

    error_code: str = "CONFLICT"


class UnauthorizedError(DomainError):
    """Authentication required or failed.

    Protocol mappings:
        - REST: 401 Unauthorized
        - GraphQL: 200 OK with errors array (or null with extension)
        - gRPC: UNAUTHENTICATED (16)
    """

    error_code: str = "UNAUTHORIZED"


class ForbiddenError(DomainError):
    """Authenticated but insufficient permissions.

    Protocol mappings:
        - REST: 403 Forbidden
        - GraphQL: 200 OK with errors array
        - gRPC: PERMISSION_DENIED (7)
    """

    error_code: str = "FORBIDDEN"


class InternalError(DomainError):
    """Internal domain error (unexpected conditions).

    Should be logged for investigation.

    Protocol mappings:
        - REST: 500 Internal Server Error
        - GraphQL: 200 OK with errors array (generic message)
        - gRPC: INTERNAL (13)
    """

    error_code: str = "INTERNAL_ERROR"
