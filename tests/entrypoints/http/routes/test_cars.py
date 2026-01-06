"""
Comprehensive test suite for GET /v1/cars route.

This test suite verifies the HTTP endpoint behavior per the REST Endpoint Design Pattern ADR:
- Route accepts query parameters and validates them
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

from kavak_lite.domain.car import Car
from kavak_lite.domain.errors import NotFoundError, ValidationError
from kavak_lite.entrypoints.http.dependencies import (
    get_get_car_by_id_use_case,
    get_search_catalog_use_case,
)
from kavak_lite.entrypoints.http.routes.cars import router
from kavak_lite.use_cases.get_car_by_id import GetCarByIdResponse
from kavak_lite.use_cases.search_car_catalog import SearchCarCatalogResponse


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app with cars router and exception handlers."""
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
def sample_cars() -> list[Car]:
    """Sample car data for test responses."""
    return [
        Car(id="1", make="Toyota", model="Corolla", year=2020, price=Decimal("25000.00")),
        Car(id="2", make="Honda", model="Civic", year=2021, price=Decimal("30000.00")),
    ]


# ==============================================================================
# Happy Path - Successful Requests
# ==============================================================================


def test_get_cars_success_with_all_filters(
    app: FastAPI, client: TestClient, mock_use_case: Mock, sample_cars: list[Car]
) -> None:
    """Route successfully processes request with all filters."""
    mock_use_case.execute.return_value = SearchCarCatalogResponse(
        cars=sample_cars,
        total_count=2,
    )

    # Override dependency
    app.dependency_overrides[get_search_catalog_use_case] = lambda: mock_use_case

    response = client.get(
        "/v1/cars",
        params={
            "brand": "Toyota",
            "model": "Corolla",
            "year_min": 2018,
            "year_max": 2023,
            "price_min": "20000.00",
            "price_max": "35000.00",
            "offset": 0,
            "limit": 20,
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "cars" in data
    assert "total" in data
    assert "offset" in data
    assert "limit" in data

    # Verify cars data
    assert len(data["cars"]) == 2
    assert data["cars"][0]["brand"] == "Toyota"
    assert data["cars"][0]["model"] == "Corolla"
    assert data["cars"][0]["price"] == "25000.00"

    # Verify pagination metadata
    assert data["total"] == 2
    assert data["offset"] == 0
    assert data["limit"] == 20

    # Verify use case was called
    mock_use_case.execute.assert_called_once()


def test_get_cars_success_with_no_filters(
    app: FastAPI, client: TestClient, mock_use_case: Mock, sample_cars: list[Car]
) -> None:
    """Route works with no filters (default pagination only)."""
    mock_use_case.execute.return_value = SearchCarCatalogResponse(
        cars=sample_cars,
        total_count=2,
    )

    app.dependency_overrides[get_search_catalog_use_case] = lambda: mock_use_case

    response = client.get("/v1/cars")

    assert response.status_code == 200
    data = response.json()

    # Should use default pagination
    assert data["offset"] == 0
    assert data["limit"] == 20
    assert len(data["cars"]) == 2


def test_get_cars_success_with_partial_filters(
    app: FastAPI, client: TestClient, mock_use_case: Mock, sample_cars: list[Car]
) -> None:
    """Route works with only some filters populated."""
    mock_use_case.execute.return_value = SearchCarCatalogResponse(
        cars=[sample_cars[0]],
        total_count=1,
    )

    app.dependency_overrides[get_search_catalog_use_case] = lambda: mock_use_case

    response = client.get(
        "/v1/cars",
        params={
            "brand": "Toyota",
            "year_min": 2018,
            # model, year_max, prices not set
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["cars"]) == 1
    assert data["cars"][0]["brand"] == "Toyota"


def test_get_cars_success_empty_results(
    app: FastAPI, client: TestClient, mock_use_case: Mock
) -> None:
    """Route handles empty results correctly."""
    mock_use_case.execute.return_value = SearchCarCatalogResponse(
        cars=[],
        total_count=0,
    )

    app.dependency_overrides[get_search_catalog_use_case] = lambda: mock_use_case

    response = client.get(
        "/v1/cars",
        params={"brand": "Ferrari"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["cars"] == []
    assert data["total"] == 0


def test_get_cars_success_with_custom_pagination(
    app: FastAPI, client: TestClient, mock_use_case: Mock, sample_cars: list[Car]
) -> None:
    """Route respects custom pagination parameters."""
    mock_use_case.execute.return_value = SearchCarCatalogResponse(
        cars=sample_cars,
        total_count=100,
    )

    app.dependency_overrides[get_search_catalog_use_case] = lambda: mock_use_case

    response = client.get(
        "/v1/cars",
        params={
            "offset": 50,
            "limit": 10,
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Verify pagination metadata is echoed
    assert data["offset"] == 50
    assert data["limit"] == 10
    assert data["total"] == 100


def test_get_cars_preserves_decimal_precision(
    app: FastAPI, client: TestClient, mock_use_case: Mock
) -> None:
    """Route preserves decimal precision in prices."""
    cars = [
        Car(id="1", make="Toyota", model="Camry", year=2020, price=Decimal("25000.50")),
    ]
    mock_use_case.execute.return_value = SearchCarCatalogResponse(
        cars=cars,
        total_count=1,
    )

    app.dependency_overrides[get_search_catalog_use_case] = lambda: mock_use_case

    response = client.get("/v1/cars")

    assert response.status_code == 200
    data = response.json()
    assert data["cars"][0]["price"] == "25000.50"


# ==============================================================================
# Validation Errors - Pydantic (Query Params)
# ==============================================================================


def test_get_cars_rejects_invalid_year_min_type(
    app: FastAPI, client: TestClient, mock_use_case: Mock
) -> None:
    """Route rejects non-integer year_min."""
    # Override dependency to avoid database connection in CI
    app.dependency_overrides[get_search_catalog_use_case] = lambda: mock_use_case

    response = client.get(
        "/v1/cars",
        params={"year_min": "abc"},
    )

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


def test_get_cars_rejects_negative_offset(
    app: FastAPI, client: TestClient, mock_use_case: Mock
) -> None:
    """Route rejects negative offset (Pydantic validation)."""
    # Override dependency to avoid database connection in CI
    app.dependency_overrides[get_search_catalog_use_case] = lambda: mock_use_case

    response = client.get(
        "/v1/cars",
        params={"offset": -1},
    )

    assert response.status_code == 422


def test_get_cars_rejects_zero_limit(app: FastAPI, client: TestClient, mock_use_case: Mock) -> None:
    """Route rejects zero limit (Pydantic validation)."""
    # Override dependency to avoid database connection in CI
    app.dependency_overrides[get_search_catalog_use_case] = lambda: mock_use_case

    response = client.get(
        "/v1/cars",
        params={"limit": 0},
    )

    assert response.status_code == 422


def test_get_cars_rejects_limit_exceeding_max(
    app: FastAPI, client: TestClient, mock_use_case: Mock
) -> None:
    """Route rejects limit > 200 (Pydantic validation)."""
    # Override dependency to avoid database connection in CI
    app.dependency_overrides[get_search_catalog_use_case] = lambda: mock_use_case

    response = client.get(
        "/v1/cars",
        params={"limit": 201},
    )

    assert response.status_code == 422


def test_get_cars_rejects_invalid_price_format(
    app: FastAPI, client: TestClient, mock_use_case: Mock
) -> None:
    """Route rejects price that doesn't match pattern."""
    # Override dependency to avoid database connection in CI
    app.dependency_overrides[get_search_catalog_use_case] = lambda: mock_use_case

    response = client.get(
        "/v1/cars",
        params={"price_min": "abc"},
    )

    assert response.status_code == 422


def test_get_cars_rejects_price_with_too_many_decimals(
    app: FastAPI, client: TestClient, mock_use_case: Mock
) -> None:
    """Route rejects price with more than 2 decimal places."""
    # Override dependency to avoid database connection in CI
    app.dependency_overrides[get_search_catalog_use_case] = lambda: mock_use_case

    response = client.get(
        "/v1/cars",
        params={"price_min": "12345.678"},
    )

    assert response.status_code == 422


# ==============================================================================
# Domain Validation Errors
# ==============================================================================


def test_get_cars_handles_domain_filter_validation_error(
    app: FastAPI, client: TestClient, mock_use_case: Mock
) -> None:
    """Route handles domain validation errors from use case (year_min > year_max)."""
    # Mock use case to raise domain validation error with structured errors
    mock_use_case.execute.side_effect = ValidationError(
        errors=[
            {
                "field": "year_min",
                "message": "Must be less than or equal to year_max",
                "code": "INVALID_RANGE",
            },
            {
                "field": "year_max",
                "message": "Must be greater than or equal to year_min",
                "code": "INVALID_RANGE",
            },
        ]
    )

    app.dependency_overrides[get_search_catalog_use_case] = lambda: mock_use_case

    response = client.get(
        "/v1/cars",
        params={
            "year_min": 2023,
            "year_max": 2020,  # Invalid range
        },
    )

    assert response.status_code == 422
    data = response.json()

    assert data["detail"] == "Validation failed"
    assert data["code"] == "VALIDATION_ERROR"
    assert "errors" in data
    assert len(data["errors"]) == 2


def test_get_cars_handles_domain_paging_validation_error(
    app: FastAPI, client: TestClient, mock_use_case: Mock
) -> None:
    """Route handles paging validation errors from use case.

    NOTE: Pydantic catches limit > 200 before it reaches the use case,
    so this test validates that if a paging error somehow reaches the route,
    it results in an error response.
    """
    mock_use_case.execute.side_effect = ValidationError(
        errors=[
            {
                "field": "limit",
                "message": "Must be less than or equal to 200",
                "code": "INVALID_VALUE",
            }
        ]
    )

    app.dependency_overrides[get_search_catalog_use_case] = lambda: mock_use_case

    # Use a valid limit to bypass Pydantic validation
    response = client.get(
        "/v1/cars",
        params={"limit": 50},  # Valid limit, but use case will raise error
    )

    assert response.status_code == 422
    data = response.json()

    assert data["detail"] == "Validation failed"
    assert data["code"] == "VALIDATION_ERROR"
    assert "errors" in data


# ==============================================================================
# Response Format
# ==============================================================================


def test_get_cars_response_has_correct_structure(
    app: FastAPI, client: TestClient, mock_use_case: Mock, sample_cars: list[Car]
) -> None:
    """Route returns response with correct JSON structure."""
    mock_use_case.execute.return_value = SearchCarCatalogResponse(
        cars=sample_cars,
        total_count=2,
    )

    app.dependency_overrides[get_search_catalog_use_case] = lambda: mock_use_case

    response = client.get("/v1/cars")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    data = response.json()

    # Verify all required fields present
    assert "cars" in data
    assert "total" in data
    assert "offset" in data
    assert "limit" in data

    # Verify types
    assert isinstance(data["cars"], list)
    assert isinstance(data["total"], int)
    assert isinstance(data["offset"], int)
    assert isinstance(data["limit"], int)


def test_get_cars_car_dto_has_correct_structure(
    app: FastAPI, client: TestClient, mock_use_case: Mock, sample_cars: list[Car]
) -> None:
    """Route returns cars with correct DTO structure."""
    mock_use_case.execute.return_value = SearchCarCatalogResponse(
        cars=[sample_cars[0]],
        total_count=1,
    )

    app.dependency_overrides[get_search_catalog_use_case] = lambda: mock_use_case

    response = client.get("/v1/cars")

    assert response.status_code == 200
    car = response.json()["cars"][0]

    # Verify all required fields
    assert "id" in car
    assert "brand" in car
    assert "model" in car
    assert "year" in car
    assert "price" in car

    # Verify types
    assert isinstance(car["id"], str)
    assert isinstance(car["brand"], str)
    assert isinstance(car["model"], str)
    assert isinstance(car["year"], int)
    assert isinstance(car["price"], str)  # Price as string!


# ==============================================================================
# Dependency Injection
# ==============================================================================


def test_get_cars_uses_dependency_injection(
    app: FastAPI, client: TestClient, mock_use_case: Mock, sample_cars: list[Car]
) -> None:
    """Route properly uses dependency injection for use case."""
    mock_use_case.execute.return_value = SearchCarCatalogResponse(
        cars=sample_cars,
        total_count=2,
    )

    # Override dependency
    app.dependency_overrides[get_search_catalog_use_case] = lambda: mock_use_case

    response = client.get("/v1/cars")

    assert response.status_code == 200

    # Verify use case was called exactly once
    mock_use_case.execute.assert_called_once()

    # Verify use case received a SearchCarCatalogRequest
    call_args = mock_use_case.execute.call_args
    request = call_args[0][0]

    # Verify request has filters and paging
    assert hasattr(request, "filters")
    assert hasattr(request, "paging")


def test_get_cars_calls_use_case_with_mapped_request(
    app: FastAPI, client: TestClient, mock_use_case: Mock, sample_cars: list[Car]
) -> None:
    """Route maps DTO to domain request before calling use case."""
    mock_use_case.execute.return_value = SearchCarCatalogResponse(
        cars=sample_cars,
        total_count=2,
    )

    app.dependency_overrides[get_search_catalog_use_case] = lambda: mock_use_case

    response = client.get(
        "/v1/cars",
        params={
            "brand": "Toyota",
            "price_min": "20000.00",
            "offset": 10,
            "limit": 5,
        },
    )

    assert response.status_code == 200

    # Verify use case was called
    mock_use_case.execute.assert_called_once()

    # Verify the request passed to use case
    call_args = mock_use_case.execute.call_args
    request = call_args[0][0]

    # Verify filters mapped correctly (brand → make)
    assert request.filters.make == "Toyota"
    assert request.filters.price_min == Decimal("20000.00")

    # Verify paging mapped correctly
    assert request.paging.offset == 10
    assert request.paging.limit == 5


# ==============================================================================
# Integration - Route Behavior
# ==============================================================================


def test_get_cars_follows_parse_execute_map_return_pattern(
    app: FastAPI, client: TestClient, mock_use_case: Mock, sample_cars: list[Car]
) -> None:
    """Route follows the prescribed pattern: parse → execute → map → return."""
    mock_use_case.execute.return_value = SearchCarCatalogResponse(
        cars=sample_cars,
        total_count=2,
    )

    app.dependency_overrides[get_search_catalog_use_case] = lambda: mock_use_case

    # Make request
    response = client.get(
        "/v1/cars",
        params={"brand": "Toyota"},
    )

    assert response.status_code == 200

    # 1. Parse: FastAPI + Pydantic handled this ✓
    # 2. Execute: Use case was called
    mock_use_case.execute.assert_called_once()

    # 3. Map: Response was mapped to DTO
    data = response.json()
    assert "cars" in data
    assert data["cars"][0]["brand"] == "Toyota"  # Domain 'make' → DTO 'brand'

    # 4. Return: HTTP response returned ✓
    assert response.headers["content-type"] == "application/json"


def test_get_cars_does_not_contain_business_logic(
    app: FastAPI, client: TestClient, mock_use_case: Mock, sample_cars: list[Car]
) -> None:
    """Route contains no filtering or business logic (delegates to use case)."""
    mock_use_case.execute.return_value = SearchCarCatalogResponse(
        cars=sample_cars,
        total_count=2,
    )

    app.dependency_overrides[get_search_catalog_use_case] = lambda: mock_use_case

    response = client.get(
        "/v1/cars",
        params={
            "brand": "Toyota",
            "price_min": "20000.00",
        },
    )

    assert response.status_code == 200

    # Route should just pass filters to use case, no filtering logic in route
    mock_use_case.execute.assert_called_once()

    # All cars returned by use case should be in response (no filtering in route)
    data = response.json()
    assert len(data["cars"]) == len(sample_cars)


# ==============================================================================
# GET /v1/cars/{car_id} - Get Car By ID
# ==============================================================================


def test_get_car_by_id_success(app: FastAPI, client: TestClient) -> None:
    """Route successfully retrieves car by ID."""
    car = Car(
        id="550e8400-e29b-41d4-a716-446655440000",
        make="Toyota",
        model="Corolla",
        year=2020,
        price=Decimal("25000.00"),
        trim="XLE",
        mileage_km=50000,
        transmission="Automático",
        fuel_type="Gasolina",
        body_type="Sedán",
        location="CDMX",
        url="https://kavak.com/mx/toyota/corolla/2020",
    )

    mock_use_case = Mock()
    mock_use_case.execute.return_value = GetCarByIdResponse(car=car)
    app.dependency_overrides[get_get_car_by_id_use_case] = lambda: mock_use_case

    response = client.get("/v1/cars/550e8400-e29b-41d4-a716-446655440000")

    assert response.status_code == 200
    data = response.json()

    # Verify all fields are present
    assert data["id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert data["brand"] == "Toyota"
    assert data["model"] == "Corolla"
    assert data["year"] == 2020
    assert data["price"] == "25000.00"
    assert data["trim"] == "XLE"
    assert data["mileage_km"] == 50000
    assert data["transmission"] == "Automático"
    assert data["fuel_type"] == "Gasolina"
    assert data["body_type"] == "Sedán"
    assert data["location"] == "CDMX"
    assert data["url"] == "https://kavak.com/mx/toyota/corolla/2020"

    # Verify use case was called with correct car_id
    mock_use_case.execute.assert_called_once()
    call_args = mock_use_case.execute.call_args[0][0]
    assert call_args.car_id == "550e8400-e29b-41d4-a716-446655440000"


def test_get_car_by_id_not_found(app: FastAPI, client: TestClient) -> None:
    """Route returns 404 when car not found."""
    mock_use_case = Mock()
    mock_use_case.execute.side_effect = NotFoundError("Car", "550e8400-e29b-41d4-a716-446655440000")
    app.dependency_overrides[get_get_car_by_id_use_case] = lambda: mock_use_case

    response = client.get("/v1/cars/550e8400-e29b-41d4-a716-446655440000")

    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "NOT_FOUND"
    assert "550e8400-e29b-41d4-a716-446655440000" in data["detail"]


def test_get_car_by_id_invalid_uuid_format(app: FastAPI, client: TestClient) -> None:
    """Route returns 422 for invalid UUID format."""
    mock_use_case = Mock()
    mock_use_case.execute.side_effect = ValidationError(
        errors=[
            {
                "field": "car_id",
                "message": "Must be a valid UUID format",
                "code": "INVALID_UUID",
            }
        ]
    )
    app.dependency_overrides[get_get_car_by_id_use_case] = lambda: mock_use_case

    response = client.get("/v1/cars/not-a-uuid")

    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "VALIDATION_ERROR"
    assert "errors" in data
    assert data["errors"][0]["field"] == "car_id"
    assert data["errors"][0]["code"] == "INVALID_UUID"


def test_get_car_by_id_preserves_decimal_precision(app: FastAPI, client: TestClient) -> None:
    """Route preserves decimal precision in price."""
    car = Car(
        id="550e8400-e29b-41d4-a716-446655440000",
        make="Toyota",
        model="Camry",
        year=2020,
        price=Decimal("25000.99"),
    )

    mock_use_case = Mock()
    mock_use_case.execute.return_value = GetCarByIdResponse(car=car)
    app.dependency_overrides[get_get_car_by_id_use_case] = lambda: mock_use_case

    response = client.get("/v1/cars/550e8400-e29b-41d4-a716-446655440000")

    assert response.status_code == 200
    data = response.json()
    assert data["price"] == "25000.99"


def test_get_car_by_id_response_structure(app: FastAPI, client: TestClient) -> None:
    """Route returns response with correct structure."""
    car = Car(
        id="550e8400-e29b-41d4-a716-446655440000",
        make="Toyota",
        model="Corolla",
        year=2020,
        price=Decimal("25000.00"),
    )

    mock_use_case = Mock()
    mock_use_case.execute.return_value = GetCarByIdResponse(car=car)
    app.dependency_overrides[get_get_car_by_id_use_case] = lambda: mock_use_case

    response = client.get("/v1/cars/550e8400-e29b-41d4-a716-446655440000")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    data = response.json()

    # Verify required fields
    assert "id" in data
    assert "brand" in data
    assert "model" in data
    assert "year" in data
    assert "price" in data

    # Verify types
    assert isinstance(data["id"], str)
    assert isinstance(data["brand"], str)
    assert isinstance(data["model"], str)
    assert isinstance(data["year"], int)
    assert isinstance(data["price"], str)


def test_get_car_by_id_uses_dependency_injection(app: FastAPI, client: TestClient) -> None:
    """Route uses dependency injection for use case."""
    car = Car(
        id="550e8400-e29b-41d4-a716-446655440000",
        make="Toyota",
        model="Corolla",
        year=2020,
        price=Decimal("25000.00"),
    )

    mock_use_case = Mock()
    mock_use_case.execute.return_value = GetCarByIdResponse(car=car)
    app.dependency_overrides[get_get_car_by_id_use_case] = lambda: mock_use_case

    response = client.get("/v1/cars/550e8400-e29b-41d4-a716-446655440000")

    assert response.status_code == 200

    # Verify use case was called exactly once
    mock_use_case.execute.assert_called_once()


def test_get_car_by_id_follows_parse_execute_map_return_pattern(
    app: FastAPI, client: TestClient
) -> None:
    """Route follows parse → execute → map → return pattern."""
    car = Car(
        id="550e8400-e29b-41d4-a716-446655440000",
        make="Toyota",
        model="Corolla",
        year=2020,
        price=Decimal("25000.00"),
    )

    mock_use_case = Mock()
    mock_use_case.execute.return_value = GetCarByIdResponse(car=car)
    app.dependency_overrides[get_get_car_by_id_use_case] = lambda: mock_use_case

    # Make request
    response = client.get("/v1/cars/550e8400-e29b-41d4-a716-446655440000")

    assert response.status_code == 200

    # 1. Parse: FastAPI extracted car_id from path ✓
    # 2. Execute: Use case was called
    mock_use_case.execute.assert_called_once()

    # 3. Map: Response was mapped to DTO
    data = response.json()
    assert data["brand"] == "Toyota"  # Domain 'make' → DTO 'brand'

    # 4. Return: HTTP response returned ✓
    assert response.headers["content-type"] == "application/json"


def test_get_car_by_id_handles_optional_fields(app: FastAPI, client: TestClient) -> None:
    """Route correctly handles cars with optional fields."""
    # Car with only required fields
    car = Car(
        id="550e8400-e29b-41d4-a716-446655440000",
        make="Toyota",
        model="Corolla",
        year=2020,
        price=Decimal("25000.00"),
    )

    mock_use_case = Mock()
    mock_use_case.execute.return_value = GetCarByIdResponse(car=car)
    app.dependency_overrides[get_get_car_by_id_use_case] = lambda: mock_use_case

    response = client.get("/v1/cars/550e8400-e29b-41d4-a716-446655440000")

    assert response.status_code == 200
    data = response.json()

    # Required fields should be present
    assert data["id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert data["brand"] == "Toyota"
    assert data["model"] == "Corolla"
    assert data["year"] == 2020
    assert data["price"] == "25000.00"

    # Optional fields may be None
    assert data.get("trim") is None
    assert data.get("mileage_km") is None
    assert data.get("transmission") is None
    assert data.get("fuel_type") is None
    assert data.get("body_type") is None
    assert data.get("location") is None
    assert data.get("url") is None
