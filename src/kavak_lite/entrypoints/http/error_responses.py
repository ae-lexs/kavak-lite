"""REST API error response models.

Structured error responses that provide consistent format for all HTTP errors.
"""

from pydantic import BaseModel, ConfigDict


class ErrorDetail(BaseModel):
    """Individual error detail for field-level errors.

    Used in validation errors to indicate which field failed and why.
    """

    field: str
    message: str
    code: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "field": "price_min",
                "message": "Must be less than or equal to price_max",
                "code": "INVALID_RANGE",
            }
        }
    )


class ErrorResponse(BaseModel):
    """Structured error response format.

    Supports:
    - Simple errors (just detail and code)
    - Multi-field validation errors (detail + errors array)
    - Error codes for i18n (code field can be used for translation keys)

    Examples:
        Simple error:
            {
                "detail": "Car not found",
                "code": "NOT_FOUND"
            }

        Validation error with multiple fields:
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
    """

    detail: str
    code: str | None = None
    errors: list[ErrorDetail] | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"detail": "Car not found", "code": "NOT_FOUND"},
                {
                    "detail": "Validation failed",
                    "code": "VALIDATION_ERROR",
                    "errors": [
                        {
                            "field": "price_min",
                            "message": "Must be less than or equal to price_max",
                            "code": "INVALID_RANGE",
                        },
                        {
                            "field": "price_max",
                            "message": "Must be greater than or equal to price_min",
                            "code": "INVALID_RANGE",
                        },
                    ],
                },
            ]
        }
    )
