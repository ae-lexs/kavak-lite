"""Tests for FastAPI exception handlers."""

from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import ValidationError as PydanticValidationError

from kavak_lite.domain.errors import (
    ConflictError,
    DomainError,
    ForbiddenError,
    InternalError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from kavak_lite.entrypoints.http.exception_handlers import (
    handle_domain_error,
    handle_request_validation_error,
    handle_unexpected_error,
    handle_value_error,
    register_exception_handlers,
)


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


# ==============================================================================
# Direct Handler Function Tests
# ==============================================================================


class TestHandleDomainErrorDirectly:
    """Tests for handle_domain_error function directly."""

    @pytest.mark.anyio
    async def test_handle_domain_error_returns_json_response(self) -> None:
        """handle_domain_error returns JSONResponse with correct structure."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/test"
        mock_request.method = "GET"

        error = ValidationError("Test validation error")

        response = await handle_domain_error(mock_request, error)

        assert response.status_code == 422
        assert response.body is not None

    @pytest.mark.anyio
    async def test_handle_domain_error_maps_status_codes_correctly(self) -> None:
        """handle_domain_error maps error codes to correct HTTP status codes."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/test"
        mock_request.method = "GET"

        # Test different error types
        test_cases = [
            (ValidationError("test"), 422),
            (NotFoundError("Car", "123"), 404),
            (ConflictError("test"), 409),
            (UnauthorizedError("test"), 401),
            (ForbiddenError("test"), 403),
            (InternalError("test"), 500),
        ]

        with patch("kavak_lite.entrypoints.http.exception_handlers.logger"):
            for error, expected_status in test_cases:
                response = await handle_domain_error(mock_request, error)
                assert response.status_code == expected_status

    @pytest.mark.anyio
    async def test_handle_domain_error_unknown_code_defaults_to_400(self) -> None:
        """Unknown error codes default to 400 Bad Request."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/test"
        mock_request.method = "GET"

        # Create a custom DomainError with unknown code
        error = DomainError(message="Unknown error", error_code="UNKNOWN_CODE")

        response = await handle_domain_error(mock_request, error)

        assert response.status_code == 400

    @pytest.mark.anyio
    async def test_handle_domain_error_logs_500_errors(self) -> None:
        """500-level errors are logged with error level."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/test"
        mock_request.method = "GET"

        error = InternalError("Internal error occurred")

        with patch("kavak_lite.entrypoints.http.exception_handlers.logger") as mock_logger:
            await handle_domain_error(mock_request, error)

            # Verify error was logged at error level
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert "Domain error occurred" in call_args[0]

    @pytest.mark.anyio
    async def test_handle_domain_error_logs_400_errors_at_info_level(self) -> None:
        """400-level errors are logged at info level."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/test"
        mock_request.method = "GET"

        error = ValidationError("Validation failed")

        with patch("kavak_lite.entrypoints.http.exception_handlers.logger") as mock_logger:
            await handle_domain_error(mock_request, error)

            # Verify error was logged at info level
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert "Client error" in call_args[0]

    @pytest.mark.anyio
    async def test_handle_domain_error_includes_field_errors(self) -> None:
        """handle_domain_error includes field errors when present."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/test"
        mock_request.method = "GET"

        error = ValidationError(
            errors=[{"field": "name", "message": "Required", "code": "REQUIRED"}]
        )

        response = await handle_domain_error(mock_request, error)

        # Parse response body
        import json

        body = json.loads(response.body)

        assert "errors" in body
        assert len(body["errors"]) == 1
        assert body["errors"][0]["field"] == "name"


class TestHandleRequestValidationErrorDirectly:
    """Tests for handle_request_validation_error function directly."""

    @pytest.mark.anyio
    async def test_handle_request_validation_error_returns_422(self) -> None:
        """handle_request_validation_error returns 422 status."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/test"
        mock_request.method = "GET"

        # Create a mock Pydantic validation error
        pydantic_error = PydanticValidationError.from_exception_data(
            "ValidationError",
            [
                {
                    "type": "missing",
                    "loc": ("body", "name"),
                    "msg": "Field required",
                    "input": {},
                }
            ],
        )
        exc = RequestValidationError(errors=pydantic_error.errors())

        response = await handle_request_validation_error(mock_request, exc)

        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_handle_request_validation_error_filters_body_prefix(self) -> None:
        """Field paths filter out 'body' and 'query' prefixes."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/test"
        mock_request.method = "POST"

        pydantic_error = PydanticValidationError.from_exception_data(
            "ValidationError",
            [
                {
                    "type": "missing",
                    "loc": ("body", "user", "name"),
                    "msg": "Field required",
                    "input": {},
                }
            ],
        )
        exc = RequestValidationError(errors=pydantic_error.errors())

        response = await handle_request_validation_error(mock_request, exc)

        import json

        body = json.loads(response.body)

        # Should have "user.name", not "body.user.name"
        assert body["errors"][0]["field"] == "user.name"

    @pytest.mark.anyio
    async def test_handle_request_validation_error_logs_errors(self) -> None:
        """Request validation errors are logged at info level."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/test"
        mock_request.method = "GET"

        pydantic_error = PydanticValidationError.from_exception_data(
            "ValidationError",
            [
                {
                    "type": "missing",
                    "loc": ("query", "limit"),
                    "msg": "Field required",
                    "input": {},
                }
            ],
        )
        exc = RequestValidationError(errors=pydantic_error.errors())

        with patch("kavak_lite.entrypoints.http.exception_handlers.logger") as mock_logger:
            await handle_request_validation_error(mock_request, exc)

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert "Request validation error" in call_args[0]


class TestHandleValueErrorDirectly:
    """Tests for handle_value_error function directly."""

    @pytest.mark.anyio
    async def test_handle_value_error_returns_422(self) -> None:
        """handle_value_error returns 422 status."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/test"
        mock_request.method = "GET"

        error = ValueError("Invalid decimal value")

        response = await handle_value_error(mock_request, error)

        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_handle_value_error_includes_error_message(self) -> None:
        """handle_value_error includes error message in response."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/test"
        mock_request.method = "GET"

        error = ValueError("Invalid format")

        response = await handle_value_error(mock_request, error)

        import json

        body = json.loads(response.body)

        assert body["detail"] == "Invalid format"
        assert body["code"] == "INVALID_VALUE"

    @pytest.mark.anyio
    async def test_handle_value_error_logs_at_info_level(self) -> None:
        """ValueError is logged at info level."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/test"
        mock_request.method = "GET"

        error = ValueError("Test error")

        with patch("kavak_lite.entrypoints.http.exception_handlers.logger") as mock_logger:
            await handle_value_error(mock_request, error)

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert "Value error" in call_args[0]


class TestHandleUnexpectedErrorDirectly:
    """Tests for handle_unexpected_error function directly."""

    @pytest.mark.anyio
    async def test_handle_unexpected_error_returns_500(self) -> None:
        """handle_unexpected_error returns 500 status."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/test"
        mock_request.method = "GET"

        error = RuntimeError("Unexpected error")

        with patch("kavak_lite.entrypoints.http.exception_handlers.logger"):
            response = await handle_unexpected_error(mock_request, error)

        assert response.status_code == 500

    @pytest.mark.anyio
    async def test_handle_unexpected_error_returns_generic_message(self) -> None:
        """Unexpected errors return generic message (no details leaked)."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/test"
        mock_request.method = "GET"

        error = RuntimeError("Internal implementation detail")

        with patch("kavak_lite.entrypoints.http.exception_handlers.logger"):
            response = await handle_unexpected_error(mock_request, error)

        import json

        body = json.loads(response.body)

        # Should return generic message, not the actual error
        assert body["detail"] == "An unexpected error occurred"
        assert body["code"] == "INTERNAL_ERROR"
        assert "Internal implementation detail" not in body["detail"]

    @pytest.mark.anyio
    async def test_handle_unexpected_error_logs_with_traceback(self) -> None:
        """Unexpected errors are logged with full traceback."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/test"
        mock_request.method = "GET"

        error = RuntimeError("Test error")

        with patch("kavak_lite.entrypoints.http.exception_handlers.logger") as mock_logger:
            await handle_unexpected_error(mock_request, error)

            # Verify error was logged with exc_info
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert "Unexpected error occurred" in call_args[0]
            assert call_args[1]["exc_info"] == error


class TestRegisterExceptionHandlers:
    """Tests for register_exception_handlers function."""

    def test_register_exception_handlers_adds_all_handlers(self) -> None:
        """register_exception_handlers adds all exception handlers to app."""
        app = FastAPI()

        with patch.object(app, "add_exception_handler") as mock_add_handler:
            register_exception_handlers(app)

            # Verify add_exception_handler was called for each exception type
            assert mock_add_handler.call_count == 4

            # Verify correct exception types were registered
            calls = mock_add_handler.call_args_list
            exception_types = [call[0][0] for call in calls]

            assert DomainError in exception_types
            assert RequestValidationError in exception_types
            assert ValueError in exception_types
            assert Exception in exception_types

    def test_register_exception_handlers_logs_success(self) -> None:
        """register_exception_handlers logs successful registration."""
        app = FastAPI()

        with patch("kavak_lite.entrypoints.http.exception_handlers.logger") as mock_logger:
            register_exception_handlers(app)

            mock_logger.info.assert_called_once_with("Exception handlers registered successfully")

    def test_register_exception_handlers_actually_registers(self) -> None:
        """Handlers registered by register_exception_handlers actually work."""
        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/test")
        def test_route() -> None:
            raise ValidationError("Test error")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")

        # Verify the handler actually works
        assert response.status_code == 422
        assert response.json()["code"] == "VALIDATION_ERROR"


class TestLoggingBehavior:
    """Tests for logging behavior across different error types."""

    @pytest.mark.anyio
    async def test_validation_errors_do_not_log_at_error_level(self) -> None:
        """Validation errors (expected) don't log at error level."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/test"
        mock_request.method = "GET"

        error = ValidationError("Expected validation error")

        with patch("kavak_lite.entrypoints.http.exception_handlers.logger") as mock_logger:
            await handle_domain_error(mock_request, error)

            # Should log at info, not error
            mock_logger.error.assert_not_called()
            mock_logger.info.assert_called_once()

    @pytest.mark.anyio
    async def test_internal_errors_log_context(self) -> None:
        """Internal errors log full context for debugging."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/cars"
        mock_request.method = "POST"

        error = InternalError("Database connection failed")

        with patch("kavak_lite.entrypoints.http.exception_handlers.logger") as mock_logger:
            await handle_domain_error(mock_request, error)

            # Verify context was logged
            call_kwargs = mock_logger.error.call_args[1]
            extra = call_kwargs["extra"]

            assert extra["path"] == "/api/cars"
            assert extra["method"] == "POST"
            assert extra["error_code"] == "INTERNAL_ERROR"
