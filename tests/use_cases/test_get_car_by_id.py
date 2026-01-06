"""Test suite for GetCarById use case."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import Mock

import pytest

from kavak_lite.domain.car import Car
from kavak_lite.domain.errors import NotFoundError, ValidationError
from kavak_lite.ports.car_catalog_repository import CarCatalogRepository
from kavak_lite.use_cases.get_car_by_id import (
    GetCarById,
    GetCarByIdRequest,
    GetCarByIdResponse,
)


@pytest.fixture()
def mock_repository() -> Mock:
    """Mock CarCatalogRepository."""
    return Mock(spec=CarCatalogRepository)


@pytest.fixture()
def sample_car() -> Car:
    """Sample car entity for testing."""
    return Car(
        id="550e8400-e29b-41d4-a716-446655440000",
        make="Toyota",
        model="Corolla",
        year=2020,
        price=Decimal("25000.00"),
    )


# ==============================================================================
# Happy Path Tests
# ==============================================================================


def test_execute_successful_get(mock_repository: Mock, sample_car: Car) -> None:
    """Use case returns car when found."""
    mock_repository.get_by_id.return_value = sample_car
    use_case = GetCarById(car_catalog_repository=mock_repository)

    request = GetCarByIdRequest(car_id="550e8400-e29b-41d4-a716-446655440000")
    result = use_case.execute(request)

    assert isinstance(result, GetCarByIdResponse)
    assert result.car == sample_car
    assert result.car.id == "550e8400-e29b-41d4-a716-446655440000"
    assert result.car.make == "Toyota"
    assert result.car.model == "Corolla"


def test_execute_calls_repository_with_car_id(mock_repository: Mock, sample_car: Car) -> None:
    """Use case delegates to repository with correct car_id."""
    mock_repository.get_by_id.return_value = sample_car
    use_case = GetCarById(car_catalog_repository=mock_repository)

    request = GetCarByIdRequest(car_id="550e8400-e29b-41d4-a716-446655440000")
    use_case.execute(request)

    mock_repository.get_by_id.assert_called_once_with("550e8400-e29b-41d4-a716-446655440000")


# ==============================================================================
# Not Found Error Tests
# ==============================================================================


def test_execute_raises_not_found_when_car_not_exists(mock_repository: Mock) -> None:
    """Use case raises NotFoundError when repository returns None."""
    mock_repository.get_by_id.return_value = None
    use_case = GetCarById(car_catalog_repository=mock_repository)

    request = GetCarByIdRequest(car_id="550e8400-e29b-41d4-a716-446655440000")

    with pytest.raises(NotFoundError) as exc_info:
        use_case.execute(request)

    error = exc_info.value
    assert error.message == "Car with identifier '550e8400-e29b-41d4-a716-446655440000' not found"
    assert error.context["resource"] == "Car"
    assert error.context["identifier"] == "550e8400-e29b-41d4-a716-446655440000"


def test_execute_not_found_includes_correct_car_id(mock_repository: Mock) -> None:
    """NotFoundError includes the requested car_id."""
    mock_repository.get_by_id.return_value = None
    use_case = GetCarById(car_catalog_repository=mock_repository)

    car_id = "12345678-1234-1234-1234-123456789012"
    request = GetCarByIdRequest(car_id=car_id)

    with pytest.raises(NotFoundError) as exc_info:
        use_case.execute(request)

    assert car_id in exc_info.value.message


# ==============================================================================
# Validation Tests
# ==============================================================================


def test_execute_validates_uuid_format(mock_repository: Mock) -> None:
    """Use case validates car_id is a valid UUID format."""
    use_case = GetCarById(car_catalog_repository=mock_repository)

    request = GetCarByIdRequest(car_id="not-a-valid-uuid")

    with pytest.raises(ValidationError) as exc_info:
        use_case.execute(request)

    error = exc_info.value
    assert len(error.errors) == 1
    assert error.errors[0]["field"] == "car_id"
    assert error.errors[0]["code"] == "INVALID_UUID"
    assert "UUID" in error.errors[0]["message"]


def test_execute_rejects_empty_string(mock_repository: Mock) -> None:
    """Use case rejects empty string as car_id."""
    use_case = GetCarById(car_catalog_repository=mock_repository)

    request = GetCarByIdRequest(car_id="")

    with pytest.raises(ValidationError) as exc_info:
        use_case.execute(request)

    assert exc_info.value.errors[0]["field"] == "car_id"


def test_execute_rejects_invalid_uuid_formats(mock_repository: Mock) -> None:
    """Use case rejects various invalid UUID formats."""
    use_case = GetCarById(car_catalog_repository=mock_repository)

    invalid_uuids = [
        "123",
        "not-a-uuid",
        "550e8400-e29b-41d4-a716",  # Too short
        "550e8400-e29b-41d4-a716-446655440000-extra",  # Too long
        "ZZZZZZZZ-ZZZZ-ZZZZ-ZZZZ-ZZZZZZZZZZZZ",  # Invalid characters
    ]

    for invalid_uuid in invalid_uuids:
        request = GetCarByIdRequest(car_id=invalid_uuid)
        with pytest.raises(ValidationError):
            use_case.execute(request)


def test_execute_does_not_call_repository_for_invalid_uuid(mock_repository: Mock) -> None:
    """Use case validates UUID before calling repository."""
    use_case = GetCarById(car_catalog_repository=mock_repository)

    request = GetCarByIdRequest(car_id="invalid-uuid")

    with pytest.raises(ValidationError):
        use_case.execute(request)

    # Repository should not be called if validation fails
    mock_repository.get_by_id.assert_not_called()


# ==============================================================================
# UUID Format Tests
# ==============================================================================


def test_execute_accepts_valid_uuid_formats(mock_repository: Mock, sample_car: Car) -> None:
    """Use case accepts various valid UUID formats."""
    mock_repository.get_by_id.return_value = sample_car
    use_case = GetCarById(car_catalog_repository=mock_repository)

    valid_uuids = [
        "550e8400-e29b-41d4-a716-446655440000",  # Standard format
        "550E8400-E29B-41D4-A716-446655440000",  # Uppercase
        "550e8400e29b41d4a716446655440000",  # No hyphens
    ]

    for valid_uuid in valid_uuids:
        request = GetCarByIdRequest(car_id=valid_uuid)
        result = use_case.execute(request)
        assert isinstance(result, GetCarByIdResponse)


# ==============================================================================
# Response Structure Tests
# ==============================================================================


def test_execute_returns_response_with_car(mock_repository: Mock, sample_car: Car) -> None:
    """Use case returns GetCarByIdResponse with car entity."""
    mock_repository.get_by_id.return_value = sample_car
    use_case = GetCarById(car_catalog_repository=mock_repository)

    request = GetCarByIdRequest(car_id="550e8400-e29b-41d4-a716-446655440000")
    result = use_case.execute(request)

    assert isinstance(result, GetCarByIdResponse)
    assert isinstance(result.car, Car)
    assert result.car is sample_car


def test_execute_preserves_car_data(mock_repository: Mock) -> None:
    """Use case preserves all car data from repository."""
    car_with_all_fields = Car(
        id="550e8400-e29b-41d4-a716-446655440000",
        make="Honda",
        model="Civic",
        year=2021,
        price=Decimal("30000.00"),
        trim="EX",
        mileage_km=25000,
        transmission="Manual",
        fuel_type="Gasolina",
        body_type="Sedán",
        location="Monterrey",
        url="https://kavak.com/mx/honda/civic/2021",
    )
    mock_repository.get_by_id.return_value = car_with_all_fields
    use_case = GetCarById(car_catalog_repository=mock_repository)

    request = GetCarByIdRequest(car_id="550e8400-e29b-41d4-a716-446655440000")
    result = use_case.execute(request)

    # Verify all fields preserved
    assert result.car.id == "550e8400-e29b-41d4-a716-446655440000"
    assert result.car.make == "Honda"
    assert result.car.model == "Civic"
    assert result.car.year == 2021
    assert result.car.price == Decimal("30000.00")
    assert result.car.trim == "EX"
    assert result.car.mileage_km == 25000
    assert result.car.transmission == "Manual"
    assert result.car.fuel_type == "Gasolina"
    assert result.car.body_type == "Sedán"
    assert result.car.location == "Monterrey"
    assert result.car.url == "https://kavak.com/mx/honda/civic/2021"
