"""
Comprehensive test suite for InMemoryCarCatalogRepository.

This test suite serves as the reference implementation for the CarCatalogRepository
contract defined in docs/adr/12-25-25-car-catalog-search.md.

Test sections:
- Filter Edge Cases: Tests for all filter semantics (make, model, year, price ranges)
- Paging Edge Cases: Tests for pagination behavior (offset, limit, boundaries)
- Decimal Precision: Tests for exact Decimal arithmetic (no float approximation)
- Empty Repository: Tests for edge case of empty data set
"""

from __future__ import annotations
from decimal import Decimal

import pytest

from kavak_lite.adapters.in_memory_car_catalog_repository import InMemoryCarCatalogRepository
from kavak_lite.domain.car import Car, CatalogFilters, Paging
from kavak_lite.ports.car_catalog_repository import SearchResult


@pytest.fixture()
def cars() -> list[Car]:
    return [
        Car(id="1", make="Toyota", model="Corolla", year=2018, price=Decimal("250000.00")),
        Car(id="2", make="Toyota", model="Camry", year=2020, price=Decimal("350000.00")),
        Car(id="3", make="Honda", model="Civic", year=2019, price=Decimal("280000.00")),
        Car(id="4", make="Mazda", model="3", year=2021, price=Decimal("400000.00")),
        Car(id="5", make="TOYOTA", model="corolla", year=2022, price=Decimal("420000.00")),
    ]


# ==============================================================================
# Filter Edge Cases
# ==============================================================================


def test_search_make_case_insensitive_exact_match(cars: list[Car]) -> None:
    repo = InMemoryCarCatalogRepository(cars)

    result = repo.search(
        filters=CatalogFilters(make="toyota"),
        paging=Paging(offset=0, limit=50),
    )

    assert [car.id for car in result.cars] == ["1", "2", "5"]  # insertion order preserved


def test_search_model_case_insensitive_exact_match(cars: list[Car]) -> None:
    repo = InMemoryCarCatalogRepository(cars)

    result = repo.search(
        filters=CatalogFilters(model="COROLLA"),
        paging=Paging(offset=0, limit=50),
    )

    assert [car.id for car in result.cars] == ["1", "5"]


def test_search_year_range_inclusive(cars: list[Car]) -> None:
    repo = InMemoryCarCatalogRepository(cars)

    result = repo.search(
        filters=CatalogFilters(year_min=2019, year_max=2021),
        paging=Paging(offset=0, limit=50),
    )

    assert [car.id for car in result.cars] == ["2", "3", "4"]


def test_search_price_range_inclusive_decimal_only(cars: list[Car]) -> None:
    repo = InMemoryCarCatalogRepository(cars)

    result = repo.search(
        filters=CatalogFilters(
            price_min=Decimal("280000.00"),
            price_max=Decimal("400000.00"),
        ),
        paging=Paging(offset=0, limit=50),
    )

    assert [car.id for car in result.cars] == ["2", "3", "4"]


def test_search_and_semantics_all_filters_must_match(cars: list[Car]) -> None:
    repo = InMemoryCarCatalogRepository(cars)

    result = repo.search(
        filters=CatalogFilters(
            make="toyota",
            model="corolla",
            year_min=2020,
        ),
        paging=Paging(offset=0, limit=50),
    )

    assert [car.id for car in result.cars] == ["5"]


def test_search_year_range_exact_boundaries(cars: list[Car]) -> None:
    """Year range boundaries are inclusive on both ends."""
    repo = InMemoryCarCatalogRepository(cars)

    result = repo.search(
        filters=CatalogFilters(year_min=2019, year_max=2020),
        paging=Paging(offset=0, limit=50),
    )

    # Should include exactly 2019 and 2020
    assert [car.id for car in result.cars] == ["2", "3"]


def test_search_complex_filter_combination(cars: list[Car]) -> None:
    """Complex combination: make + price range + year range."""
    repo = InMemoryCarCatalogRepository(cars)

    result = repo.search(
        filters=CatalogFilters(
            make="Toyota",
            price_min=Decimal("300000.00"),
            year_min=2020,
        ),
        paging=Paging(offset=0, limit=50),
    )

    assert [car.id for car in result.cars] == ["2", "5"]  # Camry 2020 and Corolla 2022


# ==============================================================================
# Paging Edge Cases
# ==============================================================================


def test_search_paging_applies_after_filtering(cars: list[Car]) -> None:
    repo = InMemoryCarCatalogRepository(cars)

    result = repo.search(
        filters=CatalogFilters(make="toyota"),
        paging=Paging(offset=1, limit=1),
    )

    assert [car.id for car in result.cars] == ["2"]


def test_search_year_min_only(cars: list[Car]) -> None:
    """Only minimum year bound (no maximum) - tests single-sided range."""
    repo = InMemoryCarCatalogRepository(cars)

    result = repo.search(
        filters=CatalogFilters(year_min=2020),
        paging=Paging(offset=0, limit=50),
    )

    assert [car.id for car in result.cars] == ["2", "4", "5"]  # 2020, 2021, 2022


def test_search_year_max_only(cars: list[Car]) -> None:
    """Only maximum year bound (no minimum) - tests single-sided range."""
    repo = InMemoryCarCatalogRepository(cars)

    result = repo.search(
        filters=CatalogFilters(year_max=2019),
        paging=Paging(offset=0, limit=50),
    )

    assert [car.id for car in result.cars] == ["1", "3"]  # 2018, 2019


def test_search_price_min_only(cars: list[Car]) -> None:
    """Only minimum price bound (no maximum) - tests single-sided range."""
    repo = InMemoryCarCatalogRepository(cars)

    result = repo.search(
        filters=CatalogFilters(price_min=Decimal("350000.00")),
        paging=Paging(offset=0, limit=50),
    )

    assert [car.id for car in result.cars] == ["2", "4", "5"]  # 350k, 400k, 420k


def test_search_price_max_only(cars: list[Car]) -> None:
    """Only maximum price bound (no minimum) - tests single-sided range."""
    repo = InMemoryCarCatalogRepository(cars)

    result = repo.search(
        filters=CatalogFilters(price_max=Decimal("280000.00")),
        paging=Paging(offset=0, limit=50),
    )

    assert [car.id for car in result.cars] == ["1", "3"]  # 250k, 280k


def test_search_no_filters_returns_all(cars: list[Car]) -> None:
    """No filters (all None) returns all cars in insertion order."""
    repo = InMemoryCarCatalogRepository(cars)

    result = repo.search(
        filters=CatalogFilters(),
        paging=Paging(offset=0, limit=50),
    )

    assert len(result.cars) == 5
    assert [car.id for car in result.cars] == ["1", "2", "3", "4", "5"]


def test_search_no_matches_returns_empty(cars: list[Car]) -> None:
    """Filters that match nothing return empty list."""
    repo = InMemoryCarCatalogRepository(cars)

    result = repo.search(
        filters=CatalogFilters(make="Ferrari"),
        paging=Paging(offset=0, limit=50),
    )

    assert result.cars == []


def test_search_paging_offset_beyond_results(cars: list[Car]) -> None:
    """Offset beyond available results returns empty list (not an error)."""
    repo = InMemoryCarCatalogRepository(cars)

    result = repo.search(
        filters=CatalogFilters(),
        paging=Paging(offset=100, limit=10),
    )

    assert result.cars == []


def test_search_paging_limit_larger_than_results(cars: list[Car]) -> None:
    """Limit larger than available results returns all available."""
    repo = InMemoryCarCatalogRepository(cars)

    result = repo.search(
        filters=CatalogFilters(),
        paging=Paging(offset=0, limit=100),  # Within max limit of 200
    )

    assert len(result.cars) == 5


def test_search_paging_max_limit_enforced(cars: list[Car]) -> None:
    """Limit exceeding maximum (200) raises ValueError."""
    repo = InMemoryCarCatalogRepository(cars)

    with pytest.raises(ValueError, match="limit must be <= 200"):
        repo.search(
            filters=CatalogFilters(),
            paging=Paging(offset=0, limit=201),  # Exceeds max
        )


def test_search_paging_first_item_only(cars: list[Car]) -> None:
    """offset=0, limit=1 returns only the first item."""
    repo = InMemoryCarCatalogRepository(cars)

    result = repo.search(
        filters=CatalogFilters(),
        paging=Paging(offset=0, limit=1),
    )

    assert [car.id for car in result.cars] == ["1"]


def test_search_paging_last_item_only(cars: list[Car]) -> None:
    """offset at last item, limit=1 returns only the last item."""
    repo = InMemoryCarCatalogRepository(cars)

    result = repo.search(
        filters=CatalogFilters(),
        paging=Paging(offset=4, limit=1),
    )

    assert [car.id for car in result.cars] == ["5"]


def test_search_paging_middle_page(cars: list[Car]) -> None:
    """Paging through middle of results works correctly."""
    repo = InMemoryCarCatalogRepository(cars)

    result = repo.search(
        filters=CatalogFilters(),
        paging=Paging(offset=2, limit=2),
    )

    assert [car.id for car in result.cars] == ["3", "4"]


def test_search_paging_with_filters_combined(cars: list[Car]) -> None:
    """Paging and filtering work correctly together."""
    repo = InMemoryCarCatalogRepository(cars)

    # Filter to Toyotas (3 results), then page to second item
    result = repo.search(
        filters=CatalogFilters(make="toyota"),
        paging=Paging(offset=0, limit=2),
    )

    assert [car.id for car in result.cars] == ["1", "2"]  # First page

    result = repo.search(
        filters=CatalogFilters(make="toyota"),
        paging=Paging(offset=2, limit=2),
    )

    assert [car.id for car in result.cars] == ["5"]  # Second page (only 1 remaining)


# ==============================================================================
# Decimal Precision
# ==============================================================================


def test_search_price_exact_boundary_match(cars: list[Car]) -> None:
    """Exact boundary values are inclusive (both min and max)."""
    repo = InMemoryCarCatalogRepository(cars)

    result = repo.search(
        filters=CatalogFilters(
            price_min=Decimal("280000.00"),
            price_max=Decimal("280000.00"),
        ),
        paging=Paging(offset=0, limit=50),
    )

    assert [car.id for car in result.cars] == ["3"]  # Exact match


def test_search_price_decimal_precision(cars: list[Car]) -> None:
    """Decimal comparisons are exact (no float approximation errors)."""
    repo = InMemoryCarCatalogRepository(cars)

    result = repo.search(
        filters=CatalogFilters(price_min=Decimal("280000.01")),
        paging=Paging(offset=0, limit=50),
    )

    # Should NOT include car 3 (280000.00 < 280000.01)
    assert [car.id for car in result.cars] == ["2", "4", "5"]


# ==============================================================================
# Empty Repository
# ==============================================================================


def test_search_empty_repository() -> None:
    """Empty repository returns empty results (no crash)."""
    repo = InMemoryCarCatalogRepository([])

    result = repo.search(
        filters=CatalogFilters(),
        paging=Paging(offset=0, limit=50),
    )

    assert result.cars == []


def test_search_empty_repository_with_filters() -> None:
    """Empty repository with filters returns empty results."""
    repo = InMemoryCarCatalogRepository([])

    result = repo.search(
        filters=CatalogFilters(make="Toyota", price_min=Decimal("100000.00")),
        paging=Paging(offset=0, limit=50),
    )

    assert result.cars == []


# ==============================================================================
# Metadata - total_count
# ==============================================================================


def test_search_returns_total_count_with_no_filters(cars: list[Car]) -> None:
    """Repository returns total_count of all cars when no filters applied."""
    repo = InMemoryCarCatalogRepository(cars)

    result = repo.search(
        filters=CatalogFilters(),
        paging=Paging(offset=0, limit=50),
    )

    assert result.total_count == 5  # All cars


def test_search_returns_total_count_with_filters(cars: list[Car]) -> None:
    """Repository returns total_count of matching cars (before paging)."""
    repo = InMemoryCarCatalogRepository(cars)

    result = repo.search(
        filters=CatalogFilters(make="Toyota"),
        paging=Paging(offset=0, limit=50),
    )

    assert result.total_count == 3  # 3 Toyotas total
    assert len(result.cars) == 3  # All 3 returned (no paging)


def test_search_total_count_before_paging(cars: list[Car]) -> None:
    """total_count reflects total matches BEFORE paging is applied."""
    repo = InMemoryCarCatalogRepository(cars)

    result = repo.search(
        filters=CatalogFilters(make="Toyota"),
        paging=Paging(offset=0, limit=1),  # Only 1 result per page
    )

    assert result.total_count == 3  # Total Toyotas (before paging)
    assert len(result.cars) == 1  # Only 1 car in this page


def test_search_total_count_with_offset_beyond_results(cars: list[Car]) -> None:
    """total_count is accurate even when offset is beyond results."""
    repo = InMemoryCarCatalogRepository(cars)

    result = repo.search(
        filters=CatalogFilters(make="Toyota"),
        paging=Paging(offset=100, limit=10),  # Way beyond results
    )

    assert result.total_count == 3  # Still 3 Toyotas total
    assert result.cars == []  # But no cars in this page


def test_search_total_count_with_empty_results(cars: list[Car]) -> None:
    """total_count is 0 when no cars match filters."""
    repo = InMemoryCarCatalogRepository(cars)

    result = repo.search(
        filters=CatalogFilters(make="Ferrari"),
        paging=Paging(offset=0, limit=50),
    )

    assert result.total_count == 0
    assert result.cars == []


def test_search_total_count_empty_repository() -> None:
    """total_count is 0 for empty repository."""
    repo = InMemoryCarCatalogRepository([])

    result = repo.search(
        filters=CatalogFilters(),
        paging=Paging(offset=0, limit=50),
    )

    assert result.total_count == 0
    assert result.cars == []


def test_search_result_structure(cars: list[Car]) -> None:
    """SearchResult has correct structure with cars and total_count."""
    repo = InMemoryCarCatalogRepository(cars)

    result = repo.search(
        filters=CatalogFilters(),
        paging=Paging(offset=0, limit=50),
    )

    # Verify SearchResult structure
    assert isinstance(result, SearchResult)
    assert isinstance(result.cars, list)
    assert isinstance(result.total_count, int)
    assert result.total_count is not None
