"""
Comprehensive test suite for POST /v1/financing/plan route.

This test suite verifies the HTTP endpoint behavior per the REST Endpoint Design Pattern ADR:
- Route accepts request payload and validates it
- Route delegates to use case via dependency injection
- Route uses mapper to convert between DTOs and domain models
- Route returns proper HTTP status codes and response format
- Route handles validation errors correctly

See: docs/ADR/12-26-25-rest-endpoint-design-pattern.md
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from kavak_lite.domain.errors import ValidationError
from kavak_lite.domain.financing import FinancingPlan
from kavak_lite.entrypoints.http.dependencies import get_calculate_financing_plan_use_case
from kavak_lite.entrypoints.http.routes.financing import router


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app with financing router and exception handlers."""
    from kavak_lite.entrypoints.http.exception_handlers import register_exception_handlers

    test_app = FastAPI()
    register_exception_handlers(test_app)
    test_app.include_router(router, prefix="/v1")
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_use_case() -> Mock:
    """Mock use case for testing route in isolation."""
    return Mock()


@pytest.fixture
def sample_plan() -> FinancingPlan:
    """Sample financing plan for test responses."""
    return FinancingPlan(
        principal=Decimal("20000.00"),
        annual_rate=Decimal("0.10"),
        term_months=60,
        monthly_payment=Decimal("424.94"),
        total_paid=Decimal("25496.40"),
        total_interest=Decimal("5496.40"),
    )


# ==============================================================================
# Happy Path - Successful Requests
# ==============================================================================


def test_calculate_financing_plan_success(
    app: FastAPI, client: TestClient, mock_use_case: Mock, sample_plan: FinancingPlan
) -> None:
    """Route successfully calculates financing plan with valid input."""
    mock_use_case.execute.return_value = sample_plan

    # Override dependency
    app.dependency_overrides[get_calculate_financing_plan_use_case] = lambda: mock_use_case

    response = client.post(
        "/v1/financing/plan",
        json={
            "price": "25000.00",
            "down_payment": "5000.00",
            "term_months": 60,
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "principal" in data
    assert "annual_rate" in data
    assert "term_months" in data
    assert "monthly_payment" in data
    assert "total_paid" in data
    assert "total_interest" in data

    # Verify response values are strings (not floats)
    assert data["principal"] == "20000.00"
    assert data["annual_rate"] == "0.10"
    assert data["term_months"] == 60
    assert data["monthly_payment"] == "424.94"
    assert data["total_paid"] == "25496.40"
    assert data["total_interest"] == "5496.40"

    # Verify use case was called
    mock_use_case.execute.assert_called_once()


def test_calculate_financing_plan_preserves_decimal_precision(
    app: FastAPI, client: TestClient, mock_use_case: Mock
) -> None:
    """Route preserves exact decimal precision in response."""
    mock_use_case.execute.return_value = FinancingPlan(
        principal=Decimal("15000.00"),
        annual_rate=Decimal("0.10"),
        term_months=48,
        monthly_payment=Decimal("380.44"),
        total_paid=Decimal("18261.12"),
        total_interest=Decimal("3261.12"),
    )

    app.dependency_overrides[get_calculate_financing_plan_use_case] = lambda: mock_use_case

    response = client.post(
        "/v1/financing/plan",
        json={
            "price": "15000.00",
            "down_payment": "0",
            "term_months": 48,
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Should be exact strings, not "380.4400000"
    assert data["monthly_payment"] == "380.44"
    assert data["total_paid"] == "18261.12"


def test_calculate_financing_plan_with_various_terms(
    app: FastAPI, client: TestClient, mock_use_case: Mock
) -> None:
    """Route works with all allowed loan terms."""
    app.dependency_overrides[get_calculate_financing_plan_use_case] = lambda: mock_use_case

    for term in [36, 48, 60, 72]:
        mock_use_case.execute.return_value = FinancingPlan(
            principal=Decimal("20000.00"),
            annual_rate=Decimal("0.10"),
            term_months=term,
            monthly_payment=Decimal("500.00"),
            total_paid=Decimal(str(500 * term)),
            total_interest=Decimal("5000.00"),
        )

        response = client.post(
            "/v1/financing/plan",
            json={
                "price": "25000.00",
                "down_payment": "5000.00",
                "term_months": term,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["term_months"] == term


def test_calculate_financing_plan_with_zero_down_payment(
    app: FastAPI, client: TestClient, mock_use_case: Mock
) -> None:
    """Route handles zero down payment correctly."""
    mock_use_case.execute.return_value = FinancingPlan(
        principal=Decimal("25000.00"),
        annual_rate=Decimal("0.10"),
        term_months=60,
        monthly_payment=Decimal("531.18"),
        total_paid=Decimal("31870.80"),
        total_interest=Decimal("6870.80"),
    )

    app.dependency_overrides[get_calculate_financing_plan_use_case] = lambda: mock_use_case

    response = client.post(
        "/v1/financing/plan",
        json={
            "price": "25000.00",
            "down_payment": "0",
            "term_months": 60,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["principal"] == "25000.00"


# ==============================================================================
# Pydantic Validation Errors - Request Body
# ==============================================================================


def test_rejects_invalid_price_format(app: FastAPI, client: TestClient) -> None:
    """Route rejects price with invalid decimal format."""
    response = client.post(
        "/v1/financing/plan",
        json={
            "price": "abc",
            "down_payment": "5000.00",
            "term_months": 60,
        },
    )

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


def test_rejects_price_with_too_many_decimals(app: FastAPI, client: TestClient) -> None:
    """Route rejects price with more than 2 decimal places."""
    response = client.post(
        "/v1/financing/plan",
        json={
            "price": "25000.123",
            "down_payment": "5000.00",
            "term_months": 60,
        },
    )

    assert response.status_code == 422


def test_rejects_negative_term_months(app: FastAPI, client: TestClient) -> None:
    """Route rejects negative term_months."""
    response = client.post(
        "/v1/financing/plan",
        json={
            "price": "25000.00",
            "down_payment": "5000.00",
            "term_months": -1,
        },
    )

    assert response.status_code == 422


def test_rejects_missing_required_fields(app: FastAPI, client: TestClient) -> None:
    """Route rejects request with missing required fields."""
    response = client.post(
        "/v1/financing/plan",
        json={
            "price": "25000.00",
            # Missing down_payment and term_months
        },
    )

    assert response.status_code == 422


def test_rejects_price_with_special_characters(app: FastAPI, client: TestClient) -> None:
    """Route rejects price with currency symbols or commas."""
    response = client.post(
        "/v1/financing/plan",
        json={
            "price": "$25,000.00",
            "down_payment": "5000.00",
            "term_months": 60,
        },
    )

    assert response.status_code == 422


def test_rejects_empty_string_for_price(app: FastAPI, client: TestClient) -> None:
    """Route rejects empty string for monetary fields."""
    response = client.post(
        "/v1/financing/plan",
        json={
            "price": "",
            "down_payment": "5000.00",
            "term_months": 60,
        },
    )

    assert response.status_code == 422


# ==============================================================================
# Domain Validation Errors
# ==============================================================================


def test_handles_invalid_term_from_domain(
    app: FastAPI, client: TestClient, mock_use_case: Mock
) -> None:
    """Route handles domain ValidationError for invalid term."""
    mock_use_case.execute.side_effect = ValidationError(
        errors=[
            {
                "field": "term_months",
                "message": "Must be one of {36, 48, 60, 72}",
                "code": "INVALID_VALUE",
            }
        ]
    )

    app.dependency_overrides[get_calculate_financing_plan_use_case] = lambda: mock_use_case

    response = client.post(
        "/v1/financing/plan",
        json={
            "price": "25000.00",
            "down_payment": "5000.00",
            "term_months": 99,  # Invalid term
        },
    )

    assert response.status_code == 422
    data = response.json()

    # Verify structured error format
    assert data["code"] == "VALIDATION_ERROR"
    assert "errors" in data
    assert len(data["errors"]) == 1
    assert data["errors"][0]["field"] == "term_months"


def test_handles_price_less_than_or_equal_zero(
    app: FastAPI, client: TestClient, mock_use_case: Mock
) -> None:
    """Route handles domain ValidationError for non-positive price."""
    mock_use_case.execute.side_effect = ValidationError(
        errors=[
            {
                "field": "price",
                "message": "Must be greater than 0",
                "code": "INVALID_VALUE",
            }
        ]
    )

    app.dependency_overrides[get_calculate_financing_plan_use_case] = lambda: mock_use_case

    response = client.post(
        "/v1/financing/plan",
        json={
            "price": "0",
            "down_payment": "0",
            "term_months": 60,
        },
    )

    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "VALIDATION_ERROR"


def test_handles_down_payment_greater_than_price(
    app: FastAPI, client: TestClient, mock_use_case: Mock
) -> None:
    """Route handles domain ValidationError for down payment >= price."""
    mock_use_case.execute.side_effect = ValidationError(
        errors=[
            {
                "field": "down_payment",
                "message": "Must be greater less than price",
                "code": "INVALID_VALUE",
            }
        ]
    )

    app.dependency_overrides[get_calculate_financing_plan_use_case] = lambda: mock_use_case

    response = client.post(
        "/v1/financing/plan",
        json={
            "price": "25000.00",
            "down_payment": "30000.00",
            "term_months": 60,
        },
    )

    assert response.status_code == 422
    data = response.json()
    assert "errors" in data


def test_handles_negative_down_payment(
    app: FastAPI, client: TestClient, mock_use_case: Mock
) -> None:
    """Route handles domain ValidationError for negative down payment."""
    mock_use_case.execute.side_effect = ValidationError(
        errors=[
            {
                "field": "down_payment",
                "message": "Must be greater than 0",
                "code": "INVALID_VALUE",
            }
        ]
    )

    app.dependency_overrides[get_calculate_financing_plan_use_case] = lambda: mock_use_case

    response = client.post(
        "/v1/financing/plan",
        json={
            "price": "25000.00",
            "down_payment": "-1000.00",
            "term_months": 60,
        },
    )

    assert response.status_code == 422


# ==============================================================================
# Response Format
# ==============================================================================


def test_response_has_correct_structure(
    app: FastAPI, client: TestClient, mock_use_case: Mock, sample_plan: FinancingPlan
) -> None:
    """Route returns response with all required fields."""
    mock_use_case.execute.return_value = sample_plan
    app.dependency_overrides[get_calculate_financing_plan_use_case] = lambda: mock_use_case

    response = client.post(
        "/v1/financing/plan",
        json={
            "price": "25000.00",
            "down_payment": "5000.00",
            "term_months": 60,
        },
    )

    assert response.status_code == 200
    data = response.json()

    # All required fields must be present
    required_fields = [
        "principal",
        "annual_rate",
        "term_months",
        "monthly_payment",
        "total_paid",
        "total_interest",
    ]
    for field in required_fields:
        assert field in data


def test_response_monetary_fields_are_strings(
    app: FastAPI, client: TestClient, mock_use_case: Mock, sample_plan: FinancingPlan
) -> None:
    """Route returns monetary values as strings, not floats."""
    mock_use_case.execute.return_value = sample_plan
    app.dependency_overrides[get_calculate_financing_plan_use_case] = lambda: mock_use_case

    response = client.post(
        "/v1/financing/plan",
        json={
            "price": "25000.00",
            "down_payment": "5000.00",
            "term_months": 60,
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Verify types
    assert isinstance(data["principal"], str)
    assert isinstance(data["annual_rate"], str)
    assert isinstance(data["monthly_payment"], str)
    assert isinstance(data["total_paid"], str)
    assert isinstance(data["total_interest"], str)
    assert isinstance(data["term_months"], int)


# ==============================================================================
# Dependency Injection
# ==============================================================================


def test_uses_dependency_injection(
    app: FastAPI, client: TestClient, mock_use_case: Mock, sample_plan: FinancingPlan
) -> None:
    """Route uses dependency injection for use case."""
    mock_use_case.execute.return_value = sample_plan
    app.dependency_overrides[get_calculate_financing_plan_use_case] = lambda: mock_use_case

    response = client.post(
        "/v1/financing/plan",
        json={
            "price": "25000.00",
            "down_payment": "5000.00",
            "term_months": 60,
        },
    )

    assert response.status_code == 200

    # Verify mock was called (dependency injection worked)
    mock_use_case.execute.assert_called_once()


def test_calls_use_case_with_mapped_request(
    app: FastAPI, client: TestClient, mock_use_case: Mock, sample_plan: FinancingPlan
) -> None:
    """Route passes properly mapped domain request to use case."""
    mock_use_case.execute.return_value = sample_plan
    app.dependency_overrides[get_calculate_financing_plan_use_case] = lambda: mock_use_case

    response = client.post(
        "/v1/financing/plan",
        json={
            "price": "25000.00",
            "down_payment": "5000.00",
            "term_months": 60,
        },
    )

    assert response.status_code == 200

    # Verify use case was called with Decimal values (not strings)
    mock_use_case.execute.assert_called_once()
    request_arg = mock_use_case.execute.call_args[0][0]
    assert request_arg.price == Decimal("25000.00")
    assert request_arg.down_payment == Decimal("5000.00")
    assert request_arg.term_months == 60
