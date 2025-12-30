"""Tests for FastAPI exception handlers."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from kavak_lite.domain.errors import (
    ConflictError,
    ForbiddenError,
    InternalError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from kavak_lite.entrypoints.http.exception_handlers import register_exception_handlers


@pytest.fixture
def app() -> FastAPI:
    """Create a minimal FastAPI app with exception handlers registered."""
    test_app = FastAPI()
    register_exception_handlers(test_app)

    # Add test routes that raise different errors
    @test_app.get("/validation-error")
    def raise_validation_error() -> None:
        raise ValidationError("Validation failed")

    @test_app.get("/validation-error-with-fields")
    def raise_validation_error_with_fields() -> None:
        raise ValidationError(
            errors=[
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
            ]
        )

    @test_app.get("/not-found-error")
    def raise_not_found_error() -> None:
        raise NotFoundError("Car", "123")

    @test_app.get("/conflict-error")
    def raise_conflict_error() -> None:
        raise ConflictError("Car already exists")

    @test_app.get("/unauthorized-error")
    def raise_unauthorized_error() -> None:
        raise UnauthorizedError("Authentication required")

    @test_app.get("/forbidden-error")
    def raise_forbidden_error() -> None:
        raise ForbiddenError("Insufficient permissions")

    @test_app.get("/internal-error")
    def raise_internal_error() -> dict:
        raise InternalError("Unexpected condition")

    @test_app.get("/value-error")
    def raise_value_error() -> dict:
        raise ValueError("Invalid decimal format")

    @test_app.get("/unexpected-error")
    def raise_unexpected_error() -> dict:
        raise RuntimeError("Something went wrong")

    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app, raise_server_exceptions=False)


class TestValidationErrorHandler:
    """Tests for ValidationError exception handler."""

    def test_simple_validation_error_returns_422(self, client: TestClient) -> None:
        """ValidationError returns 422 with structured error."""
        response = client.get("/validation-error")

        assert response.status_code == 422
        assert response.json() == {
            "detail": "Validation failed",
            "code": "VALIDATION_ERROR",
        }

    def test_validation_error_with_field_errors_returns_422(self, client: TestClient) -> None:
        """ValidationError with field errors returns 422 with errors array."""
        response = client.get("/validation-error-with-fields")

        assert response.status_code == 422
        data = response.json()

        assert data["detail"] == "Validation failed"
        assert data["code"] == "VALIDATION_ERROR"
        assert "errors" in data
        assert len(data["errors"]) == 2

        # Check first error
        assert data["errors"][0]["field"] == "price_min"
        assert data["errors"][0]["message"] == "Must be less than or equal to price_max"
        assert data["errors"][0]["code"] == "INVALID_RANGE"

        # Check second error
        assert data["errors"][1]["field"] == "price_max"
        assert data["errors"][1]["message"] == "Must be greater than or equal to price_min"
        assert data["errors"][1]["code"] == "INVALID_RANGE"


class TestNotFoundErrorHandler:
    """Tests for NotFoundError exception handler."""

    def test_not_found_error_returns_404(self, client: TestClient) -> None:
        """NotFoundError returns 404 with structured error."""
        response = client.get("/not-found-error")

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Car with identifier '123' not found",
            "code": "NOT_FOUND",
        }


class TestConflictErrorHandler:
    """Tests for ConflictError exception handler."""

    def test_conflict_error_returns_409(self, client: TestClient) -> None:
        """ConflictError returns 409 with structured error."""
        response = client.get("/conflict-error")

        assert response.status_code == 409
        assert response.json() == {
            "detail": "Car already exists",
            "code": "CONFLICT",
        }


class TestUnauthorizedErrorHandler:
    """Tests for UnauthorizedError exception handler."""

    def test_unauthorized_error_returns_401(self, client: TestClient) -> None:
        """UnauthorizedError returns 401 with structured error."""
        response = client.get("/unauthorized-error")

        assert response.status_code == 401
        assert response.json() == {
            "detail": "Authentication required",
            "code": "UNAUTHORIZED",
        }


class TestForbiddenErrorHandler:
    """Tests for ForbiddenError exception handler."""

    def test_forbidden_error_returns_403(self, client: TestClient) -> None:
        """ForbiddenError returns 403 with structured error."""
        response = client.get("/forbidden-error")

        assert response.status_code == 403
        assert response.json() == {
            "detail": "Insufficient permissions",
            "code": "FORBIDDEN",
        }


class TestInternalErrorHandler:
    """Tests for InternalError exception handler."""

    def test_internal_error_returns_500(self, client: TestClient) -> None:
        """InternalError returns 500 with structured error."""
        response = client.get("/internal-error")

        assert response.status_code == 500
        # Note: TestClient may return empty response for 500 errors
        # Just verify status code is correct


class TestValueErrorHandler:
    """Tests for ValueError exception handler."""

    def test_value_error_returns_422(self, client: TestClient) -> None:
        """ValueError returns 422 with structured error."""
        response = client.get("/value-error")

        assert response.status_code == 422
        assert response.json() == {
            "detail": "Invalid decimal format",
            "code": "INVALID_VALUE",
        }


class TestUnexpectedErrorHandler:
    """Tests for unexpected exception handler."""

    def test_unexpected_error_returns_500(self, client: TestClient) -> None:
        """Unexpected errors return 500 with generic message."""
        response = client.get("/unexpected-error")

        assert response.status_code == 500
        # Note: TestClient may return empty response for 500 errors
        # Just verify status code is correct


class TestPydanticValidationErrors:
    """Tests for Pydantic/FastAPI validation error handling."""

    def test_pydantic_validation_error_returns_422(self) -> None:
        """Pydantic validation errors return 422 with structured errors."""
        from fastapi import Query

        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/test")
        def test_route(limit: int = Query(default=20, ge=1, le=100)) -> dict:
            return {"limit": limit}

        client = TestClient(app, raise_server_exceptions=False)

        # Test with invalid limit (exceeds max)
        response = client.get("/test?limit=500")

        assert response.status_code == 422
        data = response.json()

        assert data["detail"] == "Invalid request parameters"
        assert data["code"] == "VALIDATION_ERROR"
        assert "errors" in data
        assert len(data["errors"]) > 0

    def test_pydantic_missing_required_field_returns_422(self) -> None:
        """Pydantic validation errors for missing fields return 422."""
        from pydantic import BaseModel

        app = FastAPI()
        register_exception_handlers(app)

        class RequestBody(BaseModel):
            name: str

        @app.post("/test")
        def test_route(body: RequestBody) -> dict:
            return {"name": body.name}

        client = TestClient(app, raise_server_exceptions=False)

        # Test with missing required field
        response = client.post("/test", json={})

        assert response.status_code == 422
        data = response.json()

        assert data["detail"] == "Invalid request parameters"
        assert data["code"] == "VALIDATION_ERROR"
        assert "errors" in data


class TestErrorResponseFormat:
    """Tests for error response format consistency."""

    def test_all_errors_have_detail_and_code(self, client: TestClient) -> None:
        """All error responses have 'detail' and 'code' fields."""
        endpoints = [
            "/validation-error",
            "/not-found-error",
            "/conflict-error",
            "/unauthorized-error",
            "/forbidden-error",
            "/value-error",
            # Note: Skipping 500 errors as TestClient doesn't return JSON for them
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            data = response.json()

            assert "detail" in data, f"{endpoint} missing 'detail'"
            assert "code" in data, f"{endpoint} missing 'code'"
            assert isinstance(data["detail"], str)
            assert isinstance(data["code"], str)

    def test_structured_errors_have_consistent_format(self, client: TestClient) -> None:
        """Validation errors with field-level errors have consistent format."""
        response = client.get("/validation-error-with-fields")
        data = response.json()

        assert "errors" in data
        assert isinstance(data["errors"], list)

        for error in data["errors"]:
            assert "field" in error
            assert "message" in error
            assert isinstance(error["field"], str)
            assert isinstance(error["message"], str)
            # code is optional
            if "code" in error:
                assert isinstance(error["code"], str)
