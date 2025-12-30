"""Tests for domain error classes."""

from kavak_lite.domain.errors import (
    ConflictError,
    DomainError,
    ForbiddenError,
    InternalError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)


class TestDomainError:
    """Tests for base DomainError class."""

    def test_creates_error_with_message(self) -> None:
        """DomainError stores message and has correct error code."""
        error = DomainError("Something went wrong")

        assert error.message == "Something went wrong"
        assert error.error_code == "DOMAIN_ERROR"
        assert error.context == {}

    def test_creates_error_with_context(self) -> None:
        """DomainError stores additional context."""
        error = DomainError("Error occurred", resource="Car", action="create")

        assert error.message == "Error occurred"
        assert error.context == {"resource": "Car", "action": "create"}

    def test_to_dict_returns_structured_format(self) -> None:
        """DomainError.to_dict() returns structured error format."""
        error = DomainError("Test error", field="test", value=123)

        result = error.to_dict()

        assert result == {
            "message": "Test error",
            "code": "DOMAIN_ERROR",
            "field": "test",
            "value": 123,
        }

    def test_str_representation(self) -> None:
        """DomainError string representation is the message."""
        error = DomainError("Test message")

        assert str(error) == "Test message"


class TestValidationError:
    """Tests for ValidationError class."""

    def test_creates_simple_validation_error(self) -> None:
        """ValidationError can be created with just a message."""
        error = ValidationError("Invalid input")

        assert error.message == "Invalid input"
        assert error.error_code == "VALIDATION_ERROR"
        assert error.errors is None

    def test_creates_validation_error_with_default_message(self) -> None:
        """ValidationError uses default message if none provided."""
        error = ValidationError()

        assert error.message == "Validation error"
        assert error.errors is None

    def test_creates_validation_error_with_field_errors(self) -> None:
        """ValidationError can store multiple field-level errors."""
        errors = [
            {"field": "price", "message": "Must be positive", "code": "INVALID_VALUE"},
            {"field": "year", "message": "Must be in the future", "code": "INVALID_VALUE"},
        ]

        error = ValidationError(errors=errors)

        assert error.message == "Validation failed"
        assert error.errors == errors

    def test_creates_validation_error_with_custom_message_and_errors(self) -> None:
        """ValidationError can have both custom message and field errors."""
        errors = [{"field": "price", "message": "Invalid"}]

        error = ValidationError(message="Custom validation failed", errors=errors)

        assert error.message == "Custom validation failed"
        assert error.errors == errors

    def test_to_dict_includes_field_errors(self) -> None:
        """ValidationError.to_dict() includes field errors if present."""
        errors = [
            {"field": "price_min", "message": "Must be less than price_max"},
            {"field": "price_max", "message": "Must be greater than price_min"},
        ]

        error = ValidationError(errors=errors)

        result = error.to_dict()

        assert result == {
            "message": "Validation failed",
            "code": "VALIDATION_ERROR",
            "errors": errors,
        }

    def test_to_dict_without_field_errors(self) -> None:
        """ValidationError.to_dict() works without field errors."""
        error = ValidationError("Simple error")

        result = error.to_dict()

        assert result == {
            "message": "Simple error",
            "code": "VALIDATION_ERROR",
        }


class TestNotFoundError:
    """Tests for NotFoundError class."""

    def test_creates_not_found_error_with_identifier(self) -> None:
        """NotFoundError creates message with resource and identifier."""
        error = NotFoundError("Car", "123")

        assert error.message == "Car with identifier '123' not found"
        assert error.error_code == "NOT_FOUND"
        assert error.context["resource"] == "Car"
        assert error.context["identifier"] == "123"

    def test_creates_not_found_error_without_identifier(self) -> None:
        """NotFoundError creates message with just resource."""
        error = NotFoundError("User")

        assert error.message == "User not found"
        assert error.error_code == "NOT_FOUND"
        assert error.context["resource"] == "User"
        assert error.context["identifier"] is None

    def test_to_dict_includes_resource_information(self) -> None:
        """NotFoundError.to_dict() includes resource context."""
        error = NotFoundError("Car", "abc-123")

        result = error.to_dict()

        assert result == {
            "message": "Car with identifier 'abc-123' not found",
            "code": "NOT_FOUND",
            "resource": "Car",
            "identifier": "abc-123",
        }


class TestConflictError:
    """Tests for ConflictError class."""

    def test_creates_conflict_error(self) -> None:
        """ConflictError has correct error code."""
        error = ConflictError("Resource already exists")

        assert error.message == "Resource already exists"
        assert error.error_code == "CONFLICT"


class TestUnauthorizedError:
    """Tests for UnauthorizedError class."""

    def test_creates_unauthorized_error(self) -> None:
        """UnauthorizedError has correct error code."""
        error = UnauthorizedError("Authentication required")

        assert error.message == "Authentication required"
        assert error.error_code == "UNAUTHORIZED"


class TestForbiddenError:
    """Tests for ForbiddenError class."""

    def test_creates_forbidden_error(self) -> None:
        """ForbiddenError has correct error code."""
        error = ForbiddenError("Insufficient permissions")

        assert error.message == "Insufficient permissions"
        assert error.error_code == "FORBIDDEN"


class TestInternalError:
    """Tests for InternalError class."""

    def test_creates_internal_error(self) -> None:
        """InternalError has correct error code."""
        error = InternalError("Unexpected condition")

        assert error.message == "Unexpected condition"
        assert error.error_code == "INTERNAL_ERROR"
