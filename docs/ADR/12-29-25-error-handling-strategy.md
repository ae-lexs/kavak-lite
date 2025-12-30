# ADR: Error Handling Strategy

**Date:** 2025-12-29
**Status:** Accepted
**Context:** Designing a unified error handling approach for REST, GraphQL, and gRPC APIs

---

## Context

Kavak Lite will expose APIs through three protocols:
- **REST/HTTP** - Currently implemented with FastAPI
- **GraphQL** - Planned
- **gRPC** - Planned

Each protocol has different error semantics and conventions:
- REST uses HTTP status codes (200, 404, 422, 500, etc.)
- GraphQL returns `200 OK` with errors in response body
- gRPC uses its own status codes (OK, INVALID_ARGUMENT, NOT_FOUND, etc.)

### Requirements

1. **Unified domain errors** - Single source of truth for business errors
2. **Protocol-specific translation** - Domain errors map appropriately to each protocol
3. **Structured error format** - Consistent, parseable error responses
4. **Field-level validation** - Support for multi-field validation errors
5. **i18n hooks** - Error codes that can be used for future internationalization
6. **Hybrid validation** - Protocol layer handles type/format, domain handles business rules

---

## Goals

1. Domain layer remains **protocol-agnostic** - errors are business concepts
2. Protocol adapters translate domain errors to protocol-specific formats
3. Consistent developer experience across all three APIs
4. Clear separation between expected errors (validation, not found) and unexpected errors (bugs, infrastructure)
5. Structured logging for debugging
6. Future-proof for i18n without current implementation overhead

---

## Decision

### Architecture: Domain Errors + Protocol Translators

```
┌─────────────────────────────────────────────────────────────┐
│ Domain Layer                                                │
│                                                             │
│  ValidationError, NotFoundError, ConflictError, etc.       │
│  ↓                                                          │
│  Protocol-agnostic error classes with:                     │
│  - Error code (for i18n)                                   │
│  - Error message (default locale)                          │
│  - Context data (field names, values)                      │
└─────────────────────────────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                ▼                       ▼                       ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│ REST Translator     │  │ GraphQL Translator  │  │ gRPC Translator     │
│                     │  │                     │  │                     │
│ ValidationError →   │  │ ValidationError →   │  │ ValidationError →   │
│   422 + JSON        │  │   200 + errors[]    │  │   INVALID_ARGUMENT  │
│                     │  │                     │  │                     │
│ NotFoundError →     │  │ NotFoundError →     │  │ NotFoundError →     │
│   404 + JSON        │  │   200 + errors[]    │  │   NOT_FOUND         │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
```

---

## Domain Error Classes

### Base Error Hierarchy

```python
# src/kavak_lite/domain/errors.py

from typing import Any


class DomainError(Exception):
    """Base class for all domain errors.

    Protocol-agnostic. Contains business error information that
    can be translated to HTTP, GraphQL, or gRPC formats.
    """
    # Default error code (can be used as i18n key)
    error_code: str = "DOMAIN_ERROR"

    def __init__(self, message: str, **context: Any) -> None:
        """
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
            **self.context
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
        **context: Any
    ) -> None:
        """
        Args:
            message: Overall validation error message (optional if errors provided)
            errors: List of field-specific errors, each with 'field' and 'message'
            **context: Additional context
        """
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
                **self.context
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

    def __init__(
        self,
        resource: str,
        identifier: str | None = None,
        **context: Any
    ) -> None:
        """
        Args:
            resource: Type of resource (e.g., "Car", "User")
            identifier: Resource identifier (e.g., UUID, ID)
        """
        if identifier:
            message = f"{resource} with identifier '{identifier}' not found"
        else:
            message = f"{resource} not found"

        super().__init__(
            message,
            resource=resource,
            identifier=identifier,
            **context
        )


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
```

### Domain Error to Protocol Status Code Mapping

| Domain Error | REST | GraphQL | gRPC |
|--------------|------|---------|------|
| `ValidationError` | 422 Unprocessable Entity | 200 + errors | `INVALID_ARGUMENT` (3) |
| `NotFoundError` | 404 Not Found | 200 + errors | `NOT_FOUND` (5) |
| `ConflictError` | 409 Conflict | 200 + errors | `ALREADY_EXISTS` (6) |
| `UnauthorizedError` | 401 Unauthorized | 200 + errors | `UNAUTHENTICATED` (16) |
| `ForbiddenError` | 403 Forbidden | 200 + errors | `PERMISSION_DENIED` (7) |
| `InternalError` | 500 Internal Server Error | 200 + errors | `INTERNAL` (13) |

---

## REST/HTTP Error Handling

### Structured Error Response Format

All REST errors return a consistent JSON format:

```python
# src/kavak_lite/entrypoints/http/error_responses.py

from pydantic import BaseModel, ConfigDict


class ErrorDetail(BaseModel):
    """Individual error detail (for field-level errors)."""
    field: str
    message: str
    code: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "field": "price_min",
                "message": "Must be less than or equal to price_max",
                "code": "INVALID_RANGE"
            }
        }
    )


class ErrorResponse(BaseModel):
    """Structured error response format.

    Supports:
    - Simple errors (just detail)
    - Multi-field validation errors (detail + errors array)
    - Additional context for debugging
    - i18n hooks (code field can be used for translation keys)
    """
    detail: str
    code: str | None = None
    errors: list[ErrorDetail] | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "detail": "Car not found",
                    "code": "NOT_FOUND"
                },
                {
                    "detail": "Validation failed",
                    "code": "VALIDATION_ERROR",
                    "errors": [
                        {
                            "field": "price_min",
                            "message": "Must be less than or equal to price_max",
                            "code": "INVALID_RANGE"
                        }
                    ]
                }
            ]
        }
    )
```

### Three-Layer Validation Strategy

**Layer 1: Pydantic/FastAPI** - Type and format validation
```python
# src/kavak_lite/entrypoints/http/dtos/catalog_search.py

from pydantic import BaseModel, Field, field_validator, ConfigDict
from decimal import Decimal, InvalidOperation


class CarsSearchQueryDTO(BaseModel):
    """Query parameters with Pydantic validation.

    Responsibilities:
    - Type checking (automatic)
    - Format validation (regex, field validators)
    - Bounds checking (ge, le constraints)
    - String trimming

    Does NOT validate:
    - Cross-field relationships (e.g., min <= max)
    - Business rules
    """

    price_min: str | None = Field(
        None,
        description="Minimum price (inclusive, decimal as string)",
        example="20000.00",
        pattern=r"^\d{1,10}(\.\d{1,2})?$"
    )

    price_max: str | None = Field(
        None,
        description="Maximum price (inclusive, decimal as string)",
        example="35000.00",
        pattern=r"^\d{1,10}(\.\d{1,2})?$"
    )

    limit: int = Field(
        20,
        ge=1,
        le=200,
        description="Maximum number of results to return"
    )

    @field_validator("price_min", "price_max")
    @classmethod
    def validate_decimal_format(cls, v: str | None) -> str | None:
        """Ensure price strings are valid Decimal format."""
        if v is None:
            return None

        try:
            Decimal(v)
            return v
        except InvalidOperation:
            raise ValueError(f"Invalid decimal format: {v}")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "price_min": "20000.00",
                "price_max": "35000.00",
                "limit": 20
            }
        }
    )
```

**Layer 2: Mapper** - Pure translation, no validation
```python
# src/kavak_lite/entrypoints/http/mappers/catalog_search_mapper.py

from decimal import Decimal
from kavak_lite.domain.catalog import CatalogFilters


class CatalogSearchMapper:
    """Translates between REST DTOs and domain models.

    Responsibilities:
    - Type conversion (str → Decimal)
    - DTO → Domain mapping
    - Domain → DTO mapping

    Does NOT:
    - Validate business rules
    - Check cross-field constraints
    """

    @staticmethod
    def to_domain_filters(dto: CarsSearchQueryDTO) -> CatalogFilters:
        """Convert DTO to domain filters (no validation)."""
        return CatalogFilters(
            price_min=Decimal(dto.price_min) if dto.price_min else None,
            price_max=Decimal(dto.price_max) if dto.price_max else None,
        )
```

**Layer 3: Domain** - Business rule validation
```python
# src/kavak_lite/domain/catalog.py

from dataclasses import dataclass
from decimal import Decimal
from kavak_lite.domain.errors import ValidationError


@dataclass
class CatalogFilters:
    """Domain filters with business rule validation."""

    price_min: Decimal | None = None
    price_max: Decimal | None = None

    def validate(self) -> None:
        """Validate business rules with structured error reporting."""
        errors = []

        # Cross-field validation
        if self.price_min and self.price_max:
            if self.price_min > self.price_max:
                errors.append({
                    "field": "price_min",
                    "message": "Must be less than or equal to price_max",
                    "code": "INVALID_RANGE"
                })
                errors.append({
                    "field": "price_max",
                    "message": "Must be greater than or equal to price_min",
                    "code": "INVALID_RANGE"
                })

        # Domain constraints
        if self.price_min and self.price_min <= Decimal("0"):
            errors.append({
                "field": "price_min",
                "message": "Must be greater than zero",
                "code": "INVALID_VALUE"
            })

        if errors:
            raise ValidationError(errors=errors)
```

### Global Exception Handlers

```python
# src/kavak_lite/entrypoints/http/exception_handlers.py

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import structlog

from kavak_lite.domain.errors import DomainError


logger = structlog.get_logger()


async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
    """Handle all domain errors with automatic HTTP status code mapping.

    Maps domain errors to appropriate HTTP status codes:
    - ValidationError → 422
    - NotFoundError → 404
    - ConflictError → 409
    - UnauthorizedError → 401
    - ForbiddenError → 403
    - InternalError → 500
    """
    error_dict = exc.to_dict()

    # Determine HTTP status code from domain error
    status_code_map = {
        "VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "CONFLICT": status.HTTP_409_CONFLICT,
        "UNAUTHORIZED": status.HTTP_401_UNAUTHORIZED,
        "FORBIDDEN": status.HTTP_403_FORBIDDEN,
        "INTERNAL_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    }

    status_code = status_code_map.get(
        exc.error_code,
        status.HTTP_400_BAD_REQUEST
    )

    # Log errors (except expected validation errors)
    if status_code >= 500:
        logger.error(
            "domain_error",
            error_code=exc.error_code,
            message=exc.message,
            context=exc.context,
            path=request.url.path,
        )

    # Build structured response
    response_content = {
        "detail": error_dict.get("message", str(exc)),
        "code": error_dict.get("code", exc.error_code),
    }

    # Add field-level errors if present
    if "errors" in error_dict:
        response_content["errors"] = error_dict["errors"]

    return JSONResponse(
        status_code=status_code,
        content=response_content
    )


async def handle_request_validation_error(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """Handle FastAPI/Pydantic validation errors.

    These are type errors, format errors, constraint violations at HTTP layer.
    Examples:
        - price_min=abc (not a valid format)
        - limit=500 (exceeds max constraint)
        - Missing required field
    """
    errors = []

    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"] if loc != "body")

        errors.append({
            "field": field_path,
            "message": error["msg"],
            "code": error["type"],
        })

    logger.info(
        "validation_error",
        errors=errors,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Invalid request parameters",
            "code": "VALIDATION_ERROR",
            "errors": errors,
        }
    )


async def handle_value_error(request: Request, exc: ValueError) -> JSONResponse:
    """Handle ValueError from domain logic or mappers."""
    logger.info("value_error", message=str(exc), path=request.url.path)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": str(exc),
            "code": "INVALID_VALUE",
        }
    )


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unexpected errors (bugs, infrastructure issues)."""
    logger.error(
        "unexpected_error",
        error_type=type(exc).__name__,
        message=str(exc),
        path=request.url.path,
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected error occurred",
            "code": "INTERNAL_ERROR",
        }
    )


def register_exception_handlers(app):
    """Register all exception handlers with FastAPI app."""
    from fastapi.exceptions import RequestValidationError

    app.add_exception_handler(DomainError, handle_domain_error)
    app.add_exception_handler(RequestValidationError, handle_request_validation_error)
    app.add_exception_handler(ValueError, handle_value_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
```

### REST Error Response Examples

**Pydantic Validation Error:**
```http
GET /v1/cars?price_min=invalid&limit=500

422 Unprocessable Entity
{
  "detail": "Invalid request parameters",
  "code": "VALIDATION_ERROR",
  "errors": [
    {
      "field": "price_min",
      "message": "String should match pattern '^\\d{1,10}(\\.\\d{1,2})?$'",
      "code": "string_pattern_mismatch"
    },
    {
      "field": "limit",
      "message": "Input should be less than or equal to 200",
      "code": "less_than_equal"
    }
  ]
}
```

**Domain Validation Error:**
```http
GET /v1/cars?price_min=50000.00&price_max=30000.00

422 Unprocessable Entity
{
  "detail": "Validation failed",
  "code": "VALIDATION_ERROR",
  "errors": [
    {
      "field": "price_min",
      "message": "Must be less than or equal to price_max",
      "code": "INVALID_RANGE"
    },
    {
      "field": "price_max",
      "message": "Must be greater than or equal to price_min",
      "code": "INVALID_RANGE"
    }
  ]
}
```

**Not Found Error:**
```http
GET /v1/cars/550e8400-e29b-41d4-a716-446655440000

404 Not Found
{
  "detail": "Car with identifier '550e8400-e29b-41d4-a716-446655440000' not found",
  "code": "NOT_FOUND"
}
```

---

## GraphQL Error Handling

### GraphQL Error Format (Standard)

GraphQL has a standardized error format defined in the spec:

```json
{
  "data": null,
  "errors": [
    {
      "message": "Car with identifier '123' not found",
      "locations": [{"line": 2, "column": 3}],
      "path": ["car"],
      "extensions": {
        "code": "NOT_FOUND",
        "resource": "Car",
        "identifier": "123"
      }
    }
  ]
}
```

**Key differences from REST:**
- HTTP status is **always 200 OK** (even for errors)
- Errors go in `errors` array
- Can return partial data + errors
- Custom data goes in `extensions` field
- Field path information in `path` array

### GraphQL Error Translator

```python
# src/kavak_lite/entrypoints/graphql/error_handlers.py

from typing import Any
from graphql import GraphQLError
from kavak_lite.domain.errors import DomainError, ValidationError


class GraphQLErrorTranslator:
    """Translates domain errors to GraphQL errors."""

    @staticmethod
    def from_domain_error(
        error: DomainError,
        path: list[str | int] | None = None
    ) -> GraphQLError:
        """Convert domain error to GraphQL error format.

        Args:
            error: Domain error to translate
            path: GraphQL field path where error occurred

        Returns:
            GraphQLError with proper extensions
        """
        error_dict = error.to_dict()

        # Build extensions with error code and context
        extensions: dict[str, Any] = {
            "code": error.error_code,
            **error.context
        }

        # For validation errors with multiple fields, include them
        if isinstance(error, ValidationError) and error.errors:
            extensions["errors"] = error.errors

        return GraphQLError(
            message=error.message,
            extensions=extensions,
            path=path,
        )

    @staticmethod
    def from_validation_errors(
        errors: list[dict[str, str]],
        path: list[str | int] | None = None
    ) -> list[GraphQLError]:
        """Convert multiple validation errors to GraphQL errors.

        Can return one error per field or a single aggregated error.
        """
        # Option 1: Single aggregated error
        return [
            GraphQLError(
                message="Validation failed",
                extensions={
                    "code": "VALIDATION_ERROR",
                    "errors": errors
                },
                path=path,
            )
        ]

        # Option 2: One error per field (commented out)
        # return [
        #     GraphQLError(
        #         message=err["message"],
        #         extensions={
        #             "code": err.get("code", "VALIDATION_ERROR"),
        #             "field": err["field"]
        #         },
        #         path=path,
        #     )
        #     for err in errors
        # ]
```

### GraphQL Integration Example (Strawberry)

```python
# src/kavak_lite/entrypoints/graphql/types.py

import strawberry
from typing import Optional
from kavak_lite.domain.errors import NotFoundError, ValidationError
from kavak_lite.entrypoints.graphql.error_handlers import GraphQLErrorTranslator


@strawberry.type
class Car:
    id: str
    make: str
    model: str
    year: int
    price: str


@strawberry.type
class Query:
    @strawberry.field
    def car(self, id: str) -> Optional[Car]:
        """Get car by ID.

        Raises:
            GraphQLError: If car not found (with NOT_FOUND code)
        """
        try:
            # Call use case
            result = search_catalog_use_case.get_by_id(id)

            if result is None:
                raise NotFoundError("Car", id)

            return Car(
                id=result.id,
                make=result.make,
                model=result.model,
                year=result.year,
                price=str(result.price)
            )

        except NotFoundError as e:
            # Convert to GraphQL error
            raise GraphQLErrorTranslator.from_domain_error(
                e,
                path=["car"]
            ) from e


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_car(
        self,
        make: str,
        model: str,
        year: int,
        price: str
    ) -> Car:
        """Create a new car.

        Raises:
            GraphQLError: If validation fails or car already exists
        """
        try:
            # Call use case
            result = create_car_use_case.execute(
                make=make,
                model=model,
                year=year,
                price=price
            )

            return Car(...)

        except ValidationError as e:
            raise GraphQLErrorTranslator.from_domain_error(
                e,
                path=["createCar"]
            ) from e
```

### GraphQL Error Response Examples

**Not Found Error:**
```graphql
query {
  car(id: "123") {
    id
    make
    model
  }
}
```

```json
{
  "data": {
    "car": null
  },
  "errors": [
    {
      "message": "Car with identifier '123' not found",
      "path": ["car"],
      "extensions": {
        "code": "NOT_FOUND",
        "resource": "Car",
        "identifier": "123"
      }
    }
  ]
}
```

**Validation Error:**
```graphql
mutation {
  createCar(
    make: "Toyota"
    model: "Camry"
    year: 2020
    price: "invalid"
  ) {
    id
  }
}
```

```json
{
  "data": {
    "createCar": null
  },
  "errors": [
    {
      "message": "Validation failed",
      "path": ["createCar"],
      "extensions": {
        "code": "VALIDATION_ERROR",
        "errors": [
          {
            "field": "price",
            "message": "Invalid decimal format",
            "code": "INVALID_VALUE"
          }
        ]
      }
    }
  ]
}
```

---

## gRPC Error Handling

### gRPC Status Codes

gRPC defines standard status codes (different from HTTP):

| gRPC Code | Value | Usage |
|-----------|-------|-------|
| `OK` | 0 | Success |
| `CANCELLED` | 1 | Request cancelled |
| `INVALID_ARGUMENT` | 3 | Invalid parameters (validation errors) |
| `NOT_FOUND` | 5 | Resource not found |
| `ALREADY_EXISTS` | 6 | Resource already exists |
| `PERMISSION_DENIED` | 7 | Insufficient permissions |
| `FAILED_PRECONDITION` | 9 | Precondition not met |
| `INTERNAL` | 13 | Internal server error |
| `UNAUTHENTICATED` | 16 | Authentication required |

### gRPC Error Format

gRPC supports rich error details via `google.rpc.Status`:

```protobuf
// google/rpc/status.proto
message Status {
  int32 code = 1;              // gRPC status code
  string message = 2;          // Human-readable message
  repeated Any details = 3;    // Additional error details
}

// google/rpc/error_details.proto
message BadRequest {
  repeated FieldViolation field_violations = 1;
}

message FieldViolation {
  string field = 1;            // Field path
  string description = 2;      // Error description
}
```

### gRPC Error Translator

```python
# src/kavak_lite/entrypoints/grpc/error_handlers.py

import grpc
from google.rpc import error_details_pb2, status_pb2
from grpc_status import rpc_status
from kavak_lite.domain.errors import (
    DomainError,
    ValidationError,
    NotFoundError,
    ConflictError,
    UnauthorizedError,
    ForbiddenError,
    InternalError,
)


class GrpcErrorTranslator:
    """Translates domain errors to gRPC status codes and rich errors."""

    # Domain error to gRPC status code mapping
    ERROR_CODE_MAP = {
        "VALIDATION_ERROR": grpc.StatusCode.INVALID_ARGUMENT,
        "NOT_FOUND": grpc.StatusCode.NOT_FOUND,
        "CONFLICT": grpc.StatusCode.ALREADY_EXISTS,
        "UNAUTHORIZED": grpc.StatusCode.UNAUTHENTICATED,
        "FORBIDDEN": grpc.StatusCode.PERMISSION_DENIED,
        "INTERNAL_ERROR": grpc.StatusCode.INTERNAL,
    }

    @staticmethod
    def from_domain_error(error: DomainError) -> grpc.RpcError:
        """Convert domain error to gRPC RpcError with rich details.

        Args:
            error: Domain error to translate

        Returns:
            gRPC RpcError with status code and details
        """
        # Map to gRPC status code
        status_code = GrpcErrorTranslator.ERROR_CODE_MAP.get(
            error.error_code,
            grpc.StatusCode.UNKNOWN
        )

        # Build rich status with details
        status = status_pb2.Status(
            code=status_code.value[0],
            message=error.message,
        )

        # Add field violations for validation errors
        if isinstance(error, ValidationError) and error.errors:
            bad_request = error_details_pb2.BadRequest()

            for err in error.errors:
                violation = bad_request.field_violations.add()
                violation.field = err["field"]
                violation.description = err["message"]

            status.details.append(bad_request)

        # Convert to RpcError
        return rpc_status.to_status(status)

    @staticmethod
    def abort_with_domain_error(
        context: grpc.ServicerContext,
        error: DomainError
    ) -> None:
        """Abort gRPC call with domain error details.

        Args:
            context: gRPC servicer context
            error: Domain error to convert and abort with
        """
        status_code = GrpcErrorTranslator.ERROR_CODE_MAP.get(
            error.error_code,
            grpc.StatusCode.UNKNOWN
        )

        # Build details for validation errors
        details = None
        if isinstance(error, ValidationError) and error.errors:
            bad_request = error_details_pb2.BadRequest()
            for err in error.errors:
                violation = bad_request.field_violations.add()
                violation.field = err["field"]
                violation.description = err["message"]
            details = bad_request.SerializeToString()

        # Abort with status and details
        context.abort_with_status(
            rpc_status.to_status(
                status_pb2.Status(
                    code=status_code.value[0],
                    message=error.message,
                    details=[details] if details else []
                )
            )
        )
```

### gRPC Service Implementation Example

```python
# src/kavak_lite/entrypoints/grpc/car_service.py

import grpc
from kavak_lite.domain.errors import NotFoundError, ValidationError
from kavak_lite.entrypoints.grpc.error_handlers import GrpcErrorTranslator
from kavak_lite.entrypoints.grpc import car_pb2, car_pb2_grpc


class CarService(car_pb2_grpc.CarServiceServicer):
    """gRPC service for car operations."""

    def GetCar(
        self,
        request: car_pb2.GetCarRequest,
        context: grpc.ServicerContext
    ) -> car_pb2.Car:
        """Get car by ID.

        Raises:
            grpc.RpcError: NOT_FOUND if car doesn't exist
        """
        try:
            # Call use case
            result = search_catalog_use_case.get_by_id(request.id)

            if result is None:
                raise NotFoundError("Car", request.id)

            return car_pb2.Car(
                id=result.id,
                make=result.make,
                model=result.model,
                year=result.year,
                price=str(result.price)
            )

        except NotFoundError as e:
            # Convert and abort
            GrpcErrorTranslator.abort_with_domain_error(context, e)

    def CreateCar(
        self,
        request: car_pb2.CreateCarRequest,
        context: grpc.ServicerContext
    ) -> car_pb2.Car:
        """Create a new car.

        Raises:
            grpc.RpcError: INVALID_ARGUMENT if validation fails
                          ALREADY_EXISTS if car exists
        """
        try:
            # Call use case
            result = create_car_use_case.execute(
                make=request.make,
                model=request.model,
                year=request.year,
                price=request.price
            )

            return car_pb2.Car(...)

        except (ValidationError, ConflictError) as e:
            GrpcErrorTranslator.abort_with_domain_error(context, e)
```

### gRPC Error Response Examples

**Not Found Error:**
```python
# Client call
stub.GetCar(car_pb2.GetCarRequest(id="123"))
```

```python
# Response (exception)
grpc.RpcError: <_InactiveRpcError of RPC that terminated with:
    status = StatusCode.NOT_FOUND
    details = "Car with identifier '123' not found"
>
```

**Validation Error with Field Violations:**
```python
# Client call
stub.CreateCar(car_pb2.CreateCarRequest(
    make="Toyota",
    model="Camry",
    year=2020,
    price="invalid"
))
```

```python
# Response (exception with rich details)
grpc.RpcError: <_InactiveRpcError of RPC that terminated with:
    status = StatusCode.INVALID_ARGUMENT
    details = "Validation failed"
    trailing_metadata = [
        ('grpc-status-details-bin', <BadRequest with field_violations=[
            FieldViolation(
                field="price",
                description="Invalid decimal format"
            )
        ]>)
    ]
>
```

### gRPC Client Error Parsing

```python
# src/kavak_lite/adapters/grpc_client/error_parser.py

from google.rpc import error_details_pb2
from grpc_status import rpc_status
import grpc


def parse_grpc_error(error: grpc.RpcError) -> dict:
    """Parse gRPC error to extract rich details.

    Args:
        error: gRPC error from service call

    Returns:
        Structured error information
    """
    status = rpc_status.from_call(error)

    result = {
        "code": error.code().name,
        "message": error.details(),
        "errors": []
    }

    # Extract field violations if present
    for detail in status.details:
        if detail.Is(error_details_pb2.BadRequest.DESCRIPTOR):
            bad_request = error_details_pb2.BadRequest()
            detail.Unpack(bad_request)

            for violation in bad_request.field_violations:
                result["errors"].append({
                    "field": violation.field,
                    "message": violation.description
                })

    return result
```

---

## Protocol Comparison

### Validation Error Across All Three Protocols

**Domain Code (same for all):**
```python
raise ValidationError(errors=[
    {
        "field": "price_min",
        "message": "Must be less than or equal to price_max",
        "code": "INVALID_RANGE"
    },
    {
        "field": "price_max",
        "message": "Must be greater than or equal to price_min",
        "code": "INVALID_RANGE"
    }
])
```

**REST Response:**
```http
422 Unprocessable Entity
Content-Type: application/json

{
  "detail": "Validation failed",
  "code": "VALIDATION_ERROR",
  "errors": [
    {
      "field": "price_min",
      "message": "Must be less than or equal to price_max",
      "code": "INVALID_RANGE"
    },
    {
      "field": "price_max",
      "message": "Must be greater than or equal to price_min",
      "code": "INVALID_RANGE"
    }
  ]
}
```

**GraphQL Response:**
```http
200 OK
Content-Type: application/json

{
  "data": { "searchCars": null },
  "errors": [
    {
      "message": "Validation failed",
      "path": ["searchCars"],
      "extensions": {
        "code": "VALIDATION_ERROR",
        "errors": [
          {
            "field": "price_min",
            "message": "Must be less than or equal to price_max",
            "code": "INVALID_RANGE"
          },
          {
            "field": "price_max",
            "message": "Must be greater than or equal to price_min",
            "code": "INVALID_RANGE"
          }
        ]
      }
    }
  ]
}
```

**gRPC Response:**
```
StatusCode.INVALID_ARGUMENT: Validation failed
Details: BadRequest {
  field_violations: [
    {
      field: "price_min",
      description: "Must be less than or equal to price_max"
    },
    {
      field: "price_max",
      description: "Must be greater than or equal to price_min"
    }
  ]
}
```

---

## Internationalization (i18n) Strategy

### Design for Future i18n

The error handling system is designed to support i18n without current implementation:

**1. Error Codes as Translation Keys**
```python
# Domain error includes code
raise ValidationError(errors=[{
    "field": "price_min",
    "message": "Must be greater than zero",  # Default English
    "code": "PRICE_POSITIVE",                # i18n key
}])
```

**2. Future Translation Service**
```python
# Future implementation (not in scope)
class ErrorTranslator:
    def __init__(self, locale: str = "en"):
        self.locale = locale
        self.translations = load_translations(locale)

    def translate(self, code: str, **params: Any) -> str:
        """Translate error code to localized message."""
        template = self.translations.get(code, code)
        return template.format(**params)

# Usage in API layer
@app.exception_handler(ValidationError)
async def handle_validation_error(request: Request, exc: ValidationError):
    # Get locale from Accept-Language header
    locale = parse_accept_language(request.headers.get("Accept-Language", "en"))

    # Translate if needed
    translator = ErrorTranslator(locale)

    # Return error with translated message
    ...
```

**3. Translation File Structure**
```json
// translations/en.json
{
  "PRICE_POSITIVE": "Must be greater than zero",
  "INVALID_RANGE": "{field} must be less than or equal to {other_field}"
}

// translations/es.json
{
  "PRICE_POSITIVE": "Debe ser mayor que cero",
  "INVALID_RANGE": "{field} debe ser menor o igual a {other_field}"
}
```

**Benefits:**
- Error codes are protocol-agnostic
- Can be used for client-side translation
- Server-side translation can be added later without changing domain code
- Minimal overhead (just include error codes)

---

## Logging Strategy

### Structured Logging for Errors

```python
import structlog

logger = structlog.get_logger()

# Expected errors (validation, not found) - INFO level
logger.info(
    "validation_error",
    error_code="VALIDATION_ERROR",
    fields=["price_min", "price_max"],
    path=request.url.path,
)

# Unexpected errors (bugs, infrastructure) - ERROR level
logger.error(
    "unexpected_error",
    error_type=type(exc).__name__,
    message=str(exc),
    path=request.url.path,
    exc_info=True,  # Include stack trace
)

# Domain errors with high severity - ERROR level
logger.error(
    "internal_domain_error",
    error_code=exc.error_code,
    message=exc.message,
    context=exc.context,
    path=request.url.path,
)
```

### Log Levels by Error Type

| Error Type | Log Level | Rationale |
|------------|-----------|-----------|
| `ValidationError` | INFO | Expected user error, not a bug |
| `NotFoundError` | INFO | Expected user error, not a bug |
| `ConflictError` | INFO | Expected business constraint |
| `UnauthorizedError` | WARNING | Security concern but expected |
| `ForbiddenError` | WARNING | Security concern but expected |
| `InternalError` | ERROR | Unexpected, requires investigation |
| `Exception` (catch-all) | ERROR | Bug or infrastructure issue |

---

## Testing Strategy

### Unit Tests for Error Translation

```python
# tests/entrypoints/http/test_exception_handlers.py

import pytest
from fastapi.testclient import TestClient
from kavak_lite.domain.errors import ValidationError, NotFoundError


def test_validation_error_returns_422_with_structured_errors():
    """ValidationError should return 422 with field-level errors."""
    client = TestClient(app)

    response = client.get("/v1/cars?price_min=50000&price_max=30000")

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Validation failed",
        "code": "VALIDATION_ERROR",
        "errors": [
            {
                "field": "price_min",
                "message": "Must be less than or equal to price_max",
                "code": "INVALID_RANGE"
            },
            {
                "field": "price_max",
                "message": "Must be greater than or equal to price_min",
                "code": "INVALID_RANGE"
            }
        ]
    }


def test_not_found_error_returns_404():
    """NotFoundError should return 404 with error code."""
    client = TestClient(app)

    response = client.get("/v1/cars/nonexistent-id")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Car with identifier 'nonexistent-id' not found",
        "code": "NOT_FOUND"
    }


# tests/entrypoints/graphql/test_error_translation.py

def test_domain_error_converts_to_graphql_error():
    """Domain errors should convert to GraphQL errors with extensions."""
    error = NotFoundError("Car", "123")

    gql_error = GraphQLErrorTranslator.from_domain_error(
        error,
        path=["car"]
    )

    assert gql_error.message == "Car with identifier '123' not found"
    assert gql_error.extensions["code"] == "NOT_FOUND"
    assert gql_error.path == ["car"]


# tests/entrypoints/grpc/test_error_translation.py

def test_domain_error_converts_to_grpc_status():
    """Domain errors should convert to gRPC status codes."""
    error = ValidationError(errors=[
        {"field": "price", "message": "Invalid format", "code": "INVALID_VALUE"}
    ])

    rpc_error = GrpcErrorTranslator.from_domain_error(error)

    assert rpc_error.code() == grpc.StatusCode.INVALID_ARGUMENT
    assert "Validation failed" in rpc_error.details()
```

---

## Implementation Checklist

### Phase 1: Domain Error Classes
- [ ] Create `src/kavak_lite/domain/errors.py`
- [ ] Implement base `DomainError` class
- [ ] Implement specific error types:
  - [ ] `ValidationError` (with multi-field support)
  - [ ] `NotFoundError`
  - [ ] `ConflictError`
  - [ ] `UnauthorizedError`
  - [ ] `ForbiddenError`
  - [ ] `InternalError`
- [ ] Add unit tests for error classes

### Phase 2: REST/HTTP Error Handling
- [ ] Create `src/kavak_lite/entrypoints/http/error_responses.py`
  - [ ] `ErrorDetail` model
  - [ ] `ErrorResponse` model
- [ ] Create `src/kavak_lite/entrypoints/http/exception_handlers.py`
  - [ ] `handle_domain_error()` with status code mapping
  - [ ] `handle_request_validation_error()`
  - [ ] `handle_value_error()`
  - [ ] `handle_unexpected_error()`
  - [ ] `register_exception_handlers()` function
- [ ] Update `src/kavak_lite/entrypoints/http/app.py`
  - [ ] Register exception handlers
- [ ] Update domain models to use `ValidationError`
  - [ ] `CatalogFilters.validate()`
  - [ ] `Paging.validate()`
- [ ] Add DTOs with `ConfigDict` (not `class Config`)
- [ ] Add comprehensive tests

### Phase 3: GraphQL Error Handling (Future)
- [ ] Create `src/kavak_lite/entrypoints/graphql/error_handlers.py`
  - [ ] `GraphQLErrorTranslator` class
  - [ ] `from_domain_error()` method
  - [ ] `from_validation_errors()` method
- [ ] Implement GraphQL resolvers with error translation
- [ ] Add tests for GraphQL error format

### Phase 4: gRPC Error Handling (Future)
- [ ] Create `src/kavak_lite/entrypoints/grpc/error_handlers.py`
  - [ ] `GrpcErrorTranslator` class
  - [ ] Domain error to gRPC status code mapping
  - [ ] Rich error details with field violations
- [ ] Implement gRPC services with error translation
- [ ] Create error parsing utilities for clients
- [ ] Add tests for gRPC error format

### Phase 5: Documentation
- [ ] Document error codes and their meanings
- [ ] Add examples to API documentation
- [ ] Create error handling guide for developers
- [ ] Document i18n hooks for future use

---

## Consequences

### Positive

✅ **Single source of truth** - Domain errors are protocol-agnostic
✅ **Consistent error format** - All protocols use structured errors
✅ **Type safety** - Strong typing with Pydantic and dataclasses
✅ **Testability** - Can test error translation independently
✅ **Maintainability** - Error handling logic is centralized
✅ **Extensibility** - Easy to add new error types
✅ **i18n-ready** - Error codes support future localization
✅ **Protocol-specific best practices** - Each protocol follows its conventions

### Negative

⚠️ **More abstraction** - Extra translation layer for each protocol
⚠️ **Learning curve** - Developers must understand error mapping
⚠️ **Verbosity** - More code than simple string errors

### Mitigations

- Comprehensive documentation with examples
- Clear error class hierarchy
- Well-tested translation layer
- Code review checklist for error handling

---

## Alternatives Considered

### 1. Protocol-Specific Error Classes

**Approach:** Create separate error hierarchies for REST, GraphQL, gRPC

**Rejected because:**
- Violates DRY (duplicate error logic)
- Domain layer becomes coupled to protocols
- Hard to maintain consistency

### 2. Exception-Free Domain (Result Types)

**Approach:** Use `Result[T, Error]` types instead of exceptions

```python
def validate(self) -> Result[None, ValidationError]:
    if self.price_min > self.price_max:
        return Err(ValidationError(...))
    return Ok(None)
```

**Rejected because:**
- Not idiomatic in Python
- Requires wrapping every operation
- Exceptions are well-suited for error propagation
- Can be reconsidered in the future

### 3. HTTP Status Codes in Domain

**Approach:** Include HTTP status code in domain errors

```python
class NotFoundError(DomainError):
    http_status = 404  # Couples domain to HTTP
```

**Rejected because:**
- Couples domain to HTTP protocol
- Doesn't work for GraphQL/gRPC
- Violates Clean Architecture

---

## References

- [REST API Error Handling Best Practices](https://www.rfc-editor.org/rfc/rfc7807)
- [GraphQL Error Specification](https://spec.graphql.org/October2021/#sec-Errors)
- [gRPC Status Codes](https://grpc.io/docs/guides/error/)
- [google.rpc.Status](https://github.com/googleapis/googleapis/blob/master/google/rpc/status.proto)
- [FastAPI Exception Handling](https://fastapi.tiangolo.com/tutorial/handling-errors/)
- [Pydantic V2 Configuration](https://docs.pydantic.dev/latest/api/config/)
- Clean Architecture by Robert C. Martin
- [Structured Logging with structlog](https://www.structlog.org/)
