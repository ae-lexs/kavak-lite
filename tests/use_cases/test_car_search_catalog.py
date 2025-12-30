"""
Comprehensive test suite for SearchCarCatalog UseCase.

This test suite verifies the UseCase behavior per the Car Catalog Search ADR:
- Validates paging parameters (offset, limit constraints)
- Validates filter parameters (range consistency, Decimal enforcement)
- Delegates filtering to repository (no filtering logic in UseCase)
- Returns properly structured response

See: docs/adr/12-25-25-car-catalog-search.md
"""

from __future__ import annotations
from decimal import Decimal
from unittest.mock import Mock

import pytest

from kavak_lite.domain.car import Car, CatalogFilters, Paging
from kavak_lite.domain.errors import ValidationError
from kavak_lite.ports.car_catalog_repository import CarCatalogRepository, SearchResult
from kavak_lite.use_cases.search_car_catalog import (
    SearchCarCatalog,
    SearchCarCatalogRequest,
    SearchCarCatalogResponse,
)


@pytest.fixture()
def mock_repository() -> Mock:
    """Mock repository for testing UseCase in isolation."""
    return Mock(spec=CarCatalogRepository)


@pytest.fixture()
def sample_cars() -> list[Car]:
    """Sample car data for test responses."""
    return [
        Car(id="1", make="Toyota", model="Corolla", year=2020, price=Decimal("250000.00")),
        Car(id="2", make="Honda", model="Civic", year=2021, price=Decimal("300000.00")),
    ]


# ==============================================================================
# Happy Path - Successful Searches
# ==============================================================================


def test_execute_successful_search(mock_repository: Mock, sample_cars: list[Car]) -> None:
    """UseCase successfully delegates to repository and returns response."""
    mock_repository.search.return_value = SearchResult(
        cars=sample_cars, total_count=len(sample_cars)
    )
    use_case = SearchCarCatalog(mock_repository)

    request = SearchCarCatalogRequest(
        filters=CatalogFilters(make="Toyota"),
        paging=Paging(offset=0, limit=20),
    )

    response = use_case.execute(request)

    # Verify repository was called with correct parameters
    mock_repository.search.assert_called_once_with(
        filters=request.filters,
        paging=request.paging,
    )

    # Verify response structure
    assert isinstance(response, SearchCarCatalogResponse)
    assert response.cars == sample_cars


def test_execute_with_empty_filters(mock_repository: Mock, sample_cars: list[Car]) -> None:
    """UseCase works with empty filters (return all)."""
    mock_repository.search.return_value = SearchResult(
        cars=sample_cars, total_count=len(sample_cars)
    )
    use_case = SearchCarCatalog(mock_repository)

    request = SearchCarCatalogRequest(
        filters=CatalogFilters(),  # No filters
        paging=Paging(offset=0, limit=20),
    )

    response = use_case.execute(request)

    mock_repository.search.assert_called_once()
    assert response.cars == sample_cars


def test_execute_with_no_results(mock_repository: Mock) -> None:
    """UseCase handles empty results correctly."""
    mock_repository.search.return_value = SearchResult(cars=[], total_count=0)
    use_case = SearchCarCatalog(mock_repository)

    request = SearchCarCatalogRequest(
        filters=CatalogFilters(make="Ferrari"),
        paging=Paging(offset=0, limit=20),
    )

    response = use_case.execute(request)

    assert response.cars == []


def test_execute_with_all_filters(mock_repository: Mock, sample_cars: list[Car]) -> None:
    """UseCase works with all filter fields populated."""
    mock_repository.search.return_value = SearchResult(
        cars=sample_cars, total_count=len(sample_cars)
    )
    use_case = SearchCarCatalog(mock_repository)

    request = SearchCarCatalogRequest(
        filters=CatalogFilters(
            make="Toyota",
            model="Corolla",
            year_min=2018,
            year_max=2022,
            price_min=Decimal("200000.00"),
            price_max=Decimal("400000.00"),
        ),
        paging=Paging(offset=0, limit=50),
    )

    response = use_case.execute(request)

    mock_repository.search.assert_called_once_with(
        filters=request.filters,
        paging=request.paging,
    )
    assert response.cars == sample_cars


def test_execute_with_custom_paging(mock_repository: Mock, sample_cars: list[Car]) -> None:
    """UseCase respects custom paging parameters."""
    mock_repository.search.return_value = SearchResult(
        cars=sample_cars, total_count=len(sample_cars)
    )
    use_case = SearchCarCatalog(mock_repository)

    request = SearchCarCatalogRequest(
        filters=CatalogFilters(),
        paging=Paging(offset=10, limit=5),
    )

    response = use_case.execute(request)

    # Verify paging was passed to repository
    call_args = mock_repository.search.call_args
    assert call_args.kwargs["paging"].offset == 10
    assert call_args.kwargs["paging"].limit == 5

    # Verify response is returned correctly
    assert response.cars == sample_cars
    assert response.total_count == len(sample_cars)


# ==============================================================================
# Validation - Paging Errors
# ==============================================================================


def test_execute_rejects_negative_offset(mock_repository: Mock) -> None:
    """UseCase validates offset >= 0."""
    use_case = SearchCarCatalog(mock_repository)

    request = SearchCarCatalogRequest(
        filters=CatalogFilters(),
        paging=Paging(offset=-1, limit=20),
    )

    with pytest.raises(ValidationError):
        use_case.execute(request)

    # Repository should NOT be called
    mock_repository.search.assert_not_called()


def test_execute_rejects_zero_limit(mock_repository: Mock) -> None:
    """UseCase validates limit > 0."""
    use_case = SearchCarCatalog(mock_repository)

    request = SearchCarCatalogRequest(
        filters=CatalogFilters(),
        paging=Paging(offset=0, limit=0),
    )

    with pytest.raises(ValidationError):  # Previously matched="limit must be > 0"):
        use_case.execute(request)

    mock_repository.search.assert_not_called()


def test_execute_rejects_negative_limit(mock_repository: Mock) -> None:
    """UseCase validates limit > 0."""
    use_case = SearchCarCatalog(mock_repository)

    request = SearchCarCatalogRequest(
        filters=CatalogFilters(),
        paging=Paging(offset=0, limit=-10),
    )

    with pytest.raises(ValidationError):  # Previously matched="limit must be > 0"):
        use_case.execute(request)

    mock_repository.search.assert_not_called()


def test_execute_rejects_limit_exceeding_max(mock_repository: Mock) -> None:
    """UseCase validates limit <= 200."""
    use_case = SearchCarCatalog(mock_repository)

    request = SearchCarCatalogRequest(
        filters=CatalogFilters(),
        paging=Paging(offset=0, limit=201),
    )

    with pytest.raises(ValidationError):  # Previously matched="limit must be <= 200"):
        use_case.execute(request)

    mock_repository.search.assert_not_called()


# ==============================================================================
# Validation - Filter Errors
# ==============================================================================


def test_execute_rejects_year_min_greater_than_max(mock_repository: Mock) -> None:
    """UseCase validates year_min <= year_max."""
    use_case = SearchCarCatalog(mock_repository)

    request = SearchCarCatalogRequest(
        filters=CatalogFilters(year_min=2022, year_max=2020),  # Invalid range
        paging=Paging(offset=0, limit=20),
    )

    with pytest.raises(
        ValidationError
    ):  # Previously matched="year_min cannot be greater than year_max"):
        use_case.execute(request)

    mock_repository.search.assert_not_called()


def test_execute_rejects_price_min_greater_than_max(mock_repository: Mock) -> None:
    """UseCase validates price_min <= price_max."""
    use_case = SearchCarCatalog(mock_repository)

    request = SearchCarCatalogRequest(
        filters=CatalogFilters(
            price_min=Decimal("500000.00"),
            price_max=Decimal("300000.00"),  # Invalid range
        ),
        paging=Paging(offset=0, limit=20),
    )

    with pytest.raises(
        ValidationError
    ):  # Previously matched="price_min cannot be greater than price_max"):
        use_case.execute(request)

    mock_repository.search.assert_not_called()


def test_execute_rejects_float_for_price_min(mock_repository: Mock) -> None:
    """UseCase validates price_min is Decimal (no float leakage)."""
    use_case = SearchCarCatalog(mock_repository)

    # Type checkers would catch this, but runtime validation is the guardrail
    request = SearchCarCatalogRequest(
        filters=CatalogFilters(
            price_min=250000.00,  # type: ignore - Intentionally wrong type for test
        ),
        paging=Paging(offset=0, limit=20),
    )

    with pytest.raises(ValidationError):  # Previously matched="price_min must be Decimal"):
        use_case.execute(request)

    mock_repository.search.assert_not_called()


def test_execute_rejects_float_for_price_max(mock_repository: Mock) -> None:
    """UseCase validates price_max is Decimal (no float leakage)."""
    use_case = SearchCarCatalog(mock_repository)

    request = SearchCarCatalogRequest(
        filters=CatalogFilters(
            price_max=400000.00,  # type: ignore - Intentionally wrong type for test
        ),
        paging=Paging(offset=0, limit=20),
    )

    with pytest.raises(ValidationError):  # Previously matched="price_max must be Decimal"):
        use_case.execute(request)

    mock_repository.search.assert_not_called()


# ==============================================================================
# Validation - Multiple Errors
# ==============================================================================


def test_execute_validates_filters_before_paging(mock_repository: Mock) -> None:
    """UseCase validates filters first (fails fast on first error)."""
    use_case = SearchCarCatalog(mock_repository)

    request = SearchCarCatalogRequest(
        filters=CatalogFilters(year_min=2022, year_max=2020),  # Invalid filters
        paging=Paging(offset=-1, limit=20),  # Also invalid paging
    )

    # Should fail on filters validation (called first)
    with pytest.raises(ValidationError):  # Previously matched="year_min"):
        use_case.execute(request)

    mock_repository.search.assert_not_called()


# ==============================================================================
# UseCase Behavior
# ==============================================================================


def test_execute_does_not_filter_in_use_case(mock_repository: Mock, sample_cars: list[Car]) -> None:
    """UseCase delegates ALL filtering to repository (no filtering logic in UseCase)."""
    mock_repository.search.return_value = SearchResult(
        cars=sample_cars, total_count=len(sample_cars)
    )
    use_case = SearchCarCatalog(mock_repository)

    request = SearchCarCatalogRequest(
        filters=CatalogFilters(make="Toyota", price_min=Decimal("100000.00")),
        paging=Paging(offset=0, limit=20),
    )

    response = use_case.execute(request)

    # UseCase should pass filters unchanged to repository
    # No filtering should happen in UseCase
    assert response.cars == sample_cars
    mock_repository.search.assert_called_once()


def test_execute_returns_list_not_sequence(mock_repository: Mock, sample_cars: list[Car]) -> None:
    """UseCase returns concrete list[Car] type (not Sequence)."""
    mock_repository.search.return_value = SearchResult(
        cars=sample_cars, total_count=len(sample_cars)
    )
    use_case = SearchCarCatalog(mock_repository)

    request = SearchCarCatalogRequest(
        filters=CatalogFilters(),
        paging=Paging(offset=0, limit=20),
    )

    response = use_case.execute(request)

    # Response should be a concrete list
    assert isinstance(response.cars, list)
    assert all(isinstance(car, Car) for car in response.cars)


def test_execute_response_is_immutable(mock_repository: Mock, sample_cars: list[Car]) -> None:
    """Response dataclass is frozen (immutable)."""
    mock_repository.search.return_value = SearchResult(
        cars=sample_cars, total_count=len(sample_cars)
    )
    use_case = SearchCarCatalog(mock_repository)

    request = SearchCarCatalogRequest(
        filters=CatalogFilters(),
        paging=Paging(offset=0, limit=20),
    )

    response = use_case.execute(request)

    # Response should be frozen
    with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
        response.cars = []  # type: ignore


# ==============================================================================
# Metadata - total_count
# ==============================================================================


def test_execute_returns_total_count(mock_repository: Mock, sample_cars: list[Car]) -> None:
    """UseCase returns total_count from repository in response."""
    mock_repository.search.return_value = SearchResult(cars=sample_cars, total_count=10)
    use_case = SearchCarCatalog(mock_repository)

    request = SearchCarCatalogRequest(
        filters=CatalogFilters(make="Toyota"),
        paging=Paging(offset=0, limit=2),
    )

    response = use_case.execute(request)

    assert response.total_count == 10  # From repository
    assert len(response.cars) == 2  # Paginated


def test_execute_total_count_reflects_pre_paging_total(mock_repository: Mock) -> None:
    """total_count shows total matches before paging."""
    # Simulate: 5 total matches, but only 2 in this page
    paginated_cars = [
        Car(id="1", make="Toyota", model="Corolla", year=2020, price=Decimal("250000.00")),
        Car(id="2", make="Toyota", model="Camry", year=2021, price=Decimal("300000.00")),
    ]
    mock_repository.search.return_value = SearchResult(cars=paginated_cars, total_count=5)
    use_case = SearchCarCatalog(mock_repository)

    request = SearchCarCatalogRequest(
        filters=CatalogFilters(make="Toyota"),
        paging=Paging(offset=0, limit=2),
    )

    response = use_case.execute(request)

    assert response.total_count == 5  # Total Toyotas
    assert len(response.cars) == 2  # Page size


def test_execute_total_count_can_be_none(mock_repository: Mock, sample_cars: list[Car]) -> None:
    """UseCase handles optional total_count (repository may not calculate it)."""
    mock_repository.search.return_value = SearchResult(cars=sample_cars, total_count=None)
    use_case = SearchCarCatalog(mock_repository)

    request = SearchCarCatalogRequest(
        filters=CatalogFilters(),
        paging=Paging(offset=0, limit=20),
    )

    response = use_case.execute(request)

    assert response.total_count is None  # Optional field
    assert response.cars == sample_cars


def test_execute_total_count_zero_for_no_matches(mock_repository: Mock) -> None:
    """total_count is 0 when no cars match filters."""
    mock_repository.search.return_value = SearchResult(cars=[], total_count=0)
    use_case = SearchCarCatalog(mock_repository)

    request = SearchCarCatalogRequest(
        filters=CatalogFilters(make="Ferrari"),
        paging=Paging(offset=0, limit=20),
    )

    response = use_case.execute(request)

    assert response.total_count == 0
    assert response.cars == []


def test_execute_response_includes_metadata(mock_repository: Mock, sample_cars: list[Car]) -> None:
    """Response structure includes both cars and total_count metadata."""
    mock_repository.search.return_value = SearchResult(cars=sample_cars, total_count=100)
    use_case = SearchCarCatalog(mock_repository)

    request = SearchCarCatalogRequest(
        filters=CatalogFilters(),
        paging=Paging(offset=0, limit=20),
    )

    response = use_case.execute(request)

    # Verify response has both fields
    assert hasattr(response, "cars")
    assert hasattr(response, "total_count")
    assert response.cars == sample_cars
    assert response.total_count == 100
