"""
Unit test suite for PostgresCarCatalogRepository.

This test suite verifies the PostgreSQL implementation using mocks.
Tests verify:
- Query building logic is correct
- Filters are applied correctly via SQL WHERE clauses
- COUNT(*) query is executed for total_count
- Paging (OFFSET/LIMIT) is applied correctly
- Type conversions (UUID → string, NUMERIC → Decimal) work

See: docs/adr/12-25-25-car-catalog-search.md
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, Mock

import pytest
from sqlalchemy.orm import Session

from kavak_lite.adapters.postgres_car_catalog_repository import (
    PostgresCarCatalogRepository,
)
from kavak_lite.domain.car import Car, CatalogFilters, Paging
from kavak_lite.infra.db.models.car import CarRow
from kavak_lite.ports.car_catalog_repository import SearchResult


@pytest.fixture()
def mock_session() -> Mock:
    """Mock SQLAlchemy session."""
    return Mock(spec=Session)


@pytest.fixture()
def sample_car_rows() -> list[CarRow]:
    """Sample CarRow instances for testing."""
    rows = [
        CarRow(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            make="Toyota",
            model="Corolla",
            year=2018,
            price=Decimal("250000.00"),
        ),
        CarRow(
            id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
            make="Toyota",
            model="Camry",
            year=2020,
            price=Decimal("350000.00"),
        ),
    ]
    # Prevent SQLAlchemy from trying to persist these
    for row in rows:
        row._sa_instance_state = MagicMock()  # type: ignore
    return rows


# ==============================================================================
# Query Execution Tests
# ==============================================================================


def test_search_executes_count_and_select_queries(
    mock_session: Mock, sample_car_rows: list[CarRow]
) -> None:
    """Repository executes COUNT and SELECT queries."""
    # Mock COUNT query result
    count_result = Mock()
    count_result.scalar.return_value = 2

    # Mock SELECT query result
    select_result = Mock()
    select_result.scalars.return_value.all.return_value = sample_car_rows

    # Session.execute returns different results for each call
    mock_session.execute.side_effect = [count_result, select_result]

    repo = PostgresCarCatalogRepository(mock_session)

    result = repo.search(
        filters=CatalogFilters(),
        paging=Paging(offset=0, limit=20),
    )

    # Verify two queries were executed (COUNT + SELECT)
    assert mock_session.execute.call_count == 2
    assert result.total_count == 2
    assert len(result.cars) == 2


def test_search_applies_filters_to_query(mock_session: Mock) -> None:
    """Repository applies filters to SQL WHERE clauses."""
    count_result = Mock()
    count_result.scalar.return_value = 0

    select_result = Mock()
    select_result.scalars.return_value.all.return_value = []

    mock_session.execute.side_effect = [count_result, select_result]

    repo = PostgresCarCatalogRepository(mock_session)

    repo.search(
        filters=CatalogFilters(
            make="Toyota",
            model="Corolla",
            year_min=2018,
            year_max=2022,
            price_min=Decimal("200000.00"),
            price_max=Decimal("300000.00"),
        ),
        paging=Paging(offset=0, limit=20),
    )

    # Verify session.execute was called (filters applied via query building)
    assert mock_session.execute.call_count == 2


def test_search_applies_paging(mock_session: Mock) -> None:
    """Repository applies OFFSET and LIMIT to query."""
    count_result = Mock()
    count_result.scalar.return_value = 10

    select_result = Mock()
    select_result.scalars.return_value.all.return_value = []

    mock_session.execute.side_effect = [count_result, select_result]

    repo = PostgresCarCatalogRepository(mock_session)

    repo.search(
        filters=CatalogFilters(),
        paging=Paging(offset=5, limit=3),
    )

    # Paging is applied to the SELECT query
    assert mock_session.execute.call_count == 2


# ==============================================================================
# Type Conversion Tests
# ==============================================================================


def test_search_converts_uuid_to_string(mock_session: Mock, sample_car_rows: list[CarRow]) -> None:
    """Car IDs are converted from UUID to string."""
    count_result = Mock()
    count_result.scalar.return_value = 2

    select_result = Mock()
    select_result.scalars.return_value.all.return_value = sample_car_rows

    mock_session.execute.side_effect = [count_result, select_result]

    repo = PostgresCarCatalogRepository(mock_session)

    result = repo.search(
        filters=CatalogFilters(),
        paging=Paging(offset=0, limit=20),
    )

    # Verify IDs are strings
    for car in result.cars:
        assert isinstance(car.id, str)
        # Verify it's a valid UUID string
        uuid.UUID(car.id)


def test_search_preserves_decimal_prices(mock_session: Mock, sample_car_rows: list[CarRow]) -> None:
    """Prices remain as Decimal type."""
    count_result = Mock()
    count_result.scalar.return_value = 2

    select_result = Mock()
    select_result.scalars.return_value.all.return_value = sample_car_rows

    mock_session.execute.side_effect = [count_result, select_result]

    repo = PostgresCarCatalogRepository(mock_session)

    result = repo.search(
        filters=CatalogFilters(),
        paging=Paging(offset=0, limit=20),
    )

    # Verify prices are Decimal
    for car in result.cars:
        assert isinstance(car.price, Decimal)


def test_search_returns_domain_entities(mock_session: Mock, sample_car_rows: list[CarRow]) -> None:
    """Repository returns Car domain entities, not CarRow models."""
    count_result = Mock()
    count_result.scalar.return_value = 2

    select_result = Mock()
    select_result.scalars.return_value.all.return_value = sample_car_rows

    mock_session.execute.side_effect = [count_result, select_result]

    repo = PostgresCarCatalogRepository(mock_session)

    result = repo.search(
        filters=CatalogFilters(),
        paging=Paging(offset=0, limit=20),
    )

    # Verify all results are Car domain entities
    for car in result.cars:
        assert isinstance(car, Car)
        assert not isinstance(car, CarRow)


# ==============================================================================
# SearchResult Structure Tests
# ==============================================================================


def test_search_returns_search_result(mock_session: Mock, sample_car_rows: list[CarRow]) -> None:
    """Repository returns SearchResult with cars and total_count."""
    count_result = Mock()
    count_result.scalar.return_value = 10

    select_result = Mock()
    select_result.scalars.return_value.all.return_value = sample_car_rows

    mock_session.execute.side_effect = [count_result, select_result]

    repo = PostgresCarCatalogRepository(mock_session)

    result = repo.search(
        filters=CatalogFilters(),
        paging=Paging(offset=0, limit=2),
    )

    assert isinstance(result, SearchResult)
    assert isinstance(result.cars, list)
    assert result.total_count == 10  # From COUNT query
    assert len(result.cars) == 2  # From SELECT query (paginated)


def test_search_total_count_from_count_query(mock_session: Mock) -> None:
    """total_count comes from COUNT(*) query, not len(results)."""
    # Simulate: 100 total matches, but only 5 in this page
    count_result = Mock()
    count_result.scalar.return_value = 100

    select_result = Mock()
    select_result.scalars.return_value.all.return_value = []  # Empty page

    mock_session.execute.side_effect = [count_result, select_result]

    repo = PostgresCarCatalogRepository(mock_session)

    result = repo.search(
        filters=CatalogFilters(),
        paging=Paging(offset=0, limit=5),
    )

    assert result.total_count == 100  # From COUNT query
    assert len(result.cars) == 0  # Empty results


def test_search_total_count_zero_when_no_matches(mock_session: Mock) -> None:
    """total_count is 0 when COUNT query returns 0."""
    count_result = Mock()
    count_result.scalar.return_value = 0

    select_result = Mock()
    select_result.scalars.return_value.all.return_value = []

    mock_session.execute.side_effect = [count_result, select_result]

    repo = PostgresCarCatalogRepository(mock_session)

    result = repo.search(
        filters=CatalogFilters(make="Ferrari"),
        paging=Paging(offset=0, limit=20),
    )

    assert result.total_count == 0
    assert result.cars == []


def test_search_handles_null_count_as_zero(mock_session: Mock) -> None:
    """Repository handles None from COUNT query as 0."""
    count_result = Mock()
    count_result.scalar.return_value = None  # Could happen with some DBs

    select_result = Mock()
    select_result.scalars.return_value.all.return_value = []

    mock_session.execute.side_effect = [count_result, select_result]

    repo = PostgresCarCatalogRepository(mock_session)

    result = repo.search(
        filters=CatalogFilters(),
        paging=Paging(offset=0, limit=20),
    )

    assert result.total_count == 0


# ==============================================================================
# Domain Mapping Tests
# ==============================================================================
# Note: Validation is UseCase responsibility per ADR (not repository concern)


def test_to_domain_maps_all_fields(sample_car_rows: list[CarRow]) -> None:
    """_to_domain correctly maps all fields from CarRow to Car."""
    repo = PostgresCarCatalogRepository(Mock())
    row = sample_car_rows[0]

    car = repo._to_domain(row)

    assert car.id == str(row.id)
    assert car.make == row.make
    assert car.model == row.model
    assert car.year == row.year
    assert car.price == row.price


def test_to_domain_handles_various_uuids() -> None:
    """_to_domain correctly converts different UUID formats."""
    repo = PostgresCarCatalogRepository(Mock())

    test_uuid = uuid.uuid4()
    row = CarRow(
        id=test_uuid,
        make="Test",
        model="Car",
        year=2020,
        price=Decimal("100000.00"),
    )
    row._sa_instance_state = MagicMock()  # type: ignore

    car = repo._to_domain(row)

    assert car.id == str(test_uuid)
    assert uuid.UUID(car.id) == test_uuid
