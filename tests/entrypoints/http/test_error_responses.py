"""Tests for REST error response models."""

from kavak_lite.entrypoints.http.error_responses import ErrorDetail, ErrorResponse


class TestErrorDetail:
    """Tests for ErrorDetail model."""

    def test_creates_error_detail_with_all_fields(self) -> None:
        """ErrorDetail can be created with field, message, and code."""
        detail = ErrorDetail(
            field="price_min",
            message="Must be greater than zero",
            code="INVALID_VALUE",
        )

        assert detail.field == "price_min"
        assert detail.message == "Must be greater than zero"
        assert detail.code == "INVALID_VALUE"

    def test_creates_error_detail_without_code(self) -> None:
        """ErrorDetail can be created without code (optional)."""
        detail = ErrorDetail(field="limit", message="Must be less than 200")

        assert detail.field == "limit"
        assert detail.message == "Must be less than 200"
        assert detail.code is None

    def test_serializes_to_dict(self) -> None:
        """ErrorDetail serializes to dict correctly."""
        detail = ErrorDetail(
            field="year_min",
            message="Must be less than year_max",
            code="INVALID_RANGE",
        )

        result = detail.model_dump()

        assert result == {
            "field": "year_min",
            "message": "Must be less than year_max",
            "code": "INVALID_RANGE",
        }

    def test_serializes_to_dict_without_code(self) -> None:
        """ErrorDetail serializes without code field when None."""
        detail = ErrorDetail(field="offset", message="Must be positive")

        result = detail.model_dump()

        assert result == {
            "field": "offset",
            "message": "Must be positive",
            "code": None,
        }

    def test_serializes_to_json(self) -> None:
        """ErrorDetail serializes to JSON correctly."""
        detail = ErrorDetail(
            field="price_max",
            message="Must be greater than price_min",
            code="INVALID_RANGE",
        )

        json_str = detail.model_dump_json()

        assert '"field":"price_max"' in json_str
        assert '"message":"Must be greater than price_min"' in json_str
        assert '"code":"INVALID_RANGE"' in json_str


class TestErrorResponse:
    """Tests for ErrorResponse model."""

    def test_creates_simple_error_response(self) -> None:
        """ErrorResponse can be created with just detail and code."""
        response = ErrorResponse(detail="Car not found", code="NOT_FOUND")

        assert response.detail == "Car not found"
        assert response.code == "NOT_FOUND"
        assert response.errors is None

    def test_creates_error_response_without_code(self) -> None:
        """ErrorResponse can be created without code (optional)."""
        response = ErrorResponse(detail="Something went wrong")

        assert response.detail == "Something went wrong"
        assert response.code is None
        assert response.errors is None

    def test_creates_error_response_with_field_errors(self) -> None:
        """ErrorResponse can include field-level errors."""
        errors = [
            ErrorDetail(
                field="price_min",
                message="Must be less than or equal to price_max",
                code="INVALID_RANGE",
            ),
            ErrorDetail(
                field="price_max",
                message="Must be greater than or equal to price_min",
                code="INVALID_RANGE",
            ),
        ]

        response = ErrorResponse(detail="Validation failed", code="VALIDATION_ERROR", errors=errors)

        assert response.detail == "Validation failed"
        assert response.code == "VALIDATION_ERROR"
        assert response.errors == errors
        assert len(response.errors) == 2

    def test_serializes_simple_error_to_dict(self) -> None:
        """ErrorResponse serializes simple error to dict correctly."""
        response = ErrorResponse(detail="Unauthorized", code="UNAUTHORIZED")

        result = response.model_dump()

        assert result == {
            "detail": "Unauthorized",
            "code": "UNAUTHORIZED",
            "errors": None,
        }

    def test_serializes_validation_error_to_dict(self) -> None:
        """ErrorResponse serializes validation error with fields to dict."""
        errors = [
            ErrorDetail(field="limit", message="Must be less than 200", code="INVALID_VALUE"),
        ]

        response = ErrorResponse(detail="Validation failed", code="VALIDATION_ERROR", errors=errors)

        result = response.model_dump()

        assert result["detail"] == "Validation failed"
        assert result["code"] == "VALIDATION_ERROR"
        assert len(result["errors"]) == 1
        assert result["errors"][0]["field"] == "limit"
        assert result["errors"][0]["message"] == "Must be less than 200"
        assert result["errors"][0]["code"] == "INVALID_VALUE"

    def test_serializes_to_json(self) -> None:
        """ErrorResponse serializes to JSON correctly."""
        response = ErrorResponse(detail="Conflict", code="CONFLICT")

        json_str = response.model_dump_json()

        assert '"detail":"Conflict"' in json_str
        assert '"code":"CONFLICT"' in json_str

    def test_serializes_complex_error_to_json(self) -> None:
        """ErrorResponse serializes complex error with multiple fields."""
        errors = [
            ErrorDetail(field="year_min", message="Invalid range", code="INVALID_RANGE"),
            ErrorDetail(field="year_max", message="Invalid range", code="INVALID_RANGE"),
        ]

        response = ErrorResponse(detail="Validation failed", code="VALIDATION_ERROR", errors=errors)

        json_str = response.model_dump_json()

        assert '"detail":"Validation failed"' in json_str
        assert '"code":"VALIDATION_ERROR"' in json_str
        assert '"field":"year_min"' in json_str
        assert '"field":"year_max"' in json_str

    def test_parses_from_dict(self) -> None:
        """ErrorResponse can be parsed from dict."""
        data = {
            "detail": "Not found",
            "code": "NOT_FOUND",
            "errors": None,
        }

        response = ErrorResponse.model_validate(data)

        assert response.detail == "Not found"
        assert response.code == "NOT_FOUND"
        assert response.errors is None

    def test_parses_validation_error_from_dict(self) -> None:
        """ErrorResponse can be parsed from dict with errors."""
        data = {
            "detail": "Validation failed",
            "code": "VALIDATION_ERROR",
            "errors": [
                {
                    "field": "price",
                    "message": "Must be positive",
                    "code": "INVALID_VALUE",
                }
            ],
        }

        response = ErrorResponse.model_validate(data)

        assert response.detail == "Validation failed"
        assert response.code == "VALIDATION_ERROR"
        assert len(response.errors) == 1
        assert response.errors[0].field == "price"
        assert response.errors[0].message == "Must be positive"
        assert response.errors[0].code == "INVALID_VALUE"


class TestErrorResponseExamples:
    """Tests for ErrorResponse example schemas."""

    def test_has_json_schema_examples(self) -> None:
        """ErrorResponse has json_schema_extra with examples."""
        schema = ErrorResponse.model_json_schema()

        assert "examples" in schema
        assert isinstance(schema["examples"], list)
        assert len(schema["examples"]) >= 2

    def test_simple_error_example_is_valid(self) -> None:
        """Simple error example matches model schema."""
        schema = ErrorResponse.model_json_schema()
        simple_example = schema["examples"][0]

        # Should be able to validate against the model
        response = ErrorResponse.model_validate(simple_example)

        assert response.detail is not None
        assert response.code is not None

    def test_validation_error_example_is_valid(self) -> None:
        """Validation error example matches model schema."""
        schema = ErrorResponse.model_json_schema()
        validation_example = schema["examples"][1]

        # Should be able to validate against the model
        response = ErrorResponse.model_validate(validation_example)

        assert response.detail is not None
        assert response.code is not None
        assert response.errors is not None
        assert len(response.errors) > 0


class TestErrorDetailExamples:
    """Tests for ErrorDetail example schemas."""

    def test_has_json_schema_example(self) -> None:
        """ErrorDetail has json_schema_extra with example."""
        schema = ErrorDetail.model_json_schema()

        assert "example" in schema
        assert isinstance(schema["example"], dict)

    def test_example_is_valid(self) -> None:
        """ErrorDetail example matches model schema."""
        schema = ErrorDetail.model_json_schema()
        example = schema["example"]

        # Should be able to validate against the model
        detail = ErrorDetail.model_validate(example)

        assert detail.field is not None
        assert detail.message is not None
        assert detail.code is not None
