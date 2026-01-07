"""PostgreSQL implementation of CarCatalogRepository."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kavak_lite.domain.car import Car, CatalogFilters, Paging
from kavak_lite.infra.db.models.car import CarRow
from kavak_lite.ports.car_catalog_repository import CarCatalogRepository, SearchResult

if TYPE_CHECKING:
    from sqlalchemy.sql import Select


class PostgresCarCatalogRepository(CarCatalogRepository):
    """
    PostgreSQL implementation of CarCatalogRepository.

    - Uses SQLAlchemy ORM for database access
    - Applies filters using SQL WHERE clauses
    - Returns total_count via COUNT(*) query
    - Converts CarRow (infrastructure) to Car (domain)
    """

    def __init__(self, session: Session) -> None:
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy session for database operations
        """
        self._session = session

    def search(self, filters: CatalogFilters, paging: Paging) -> SearchResult:
        """
        Search catalog with filters and paging.

        Executes two queries:
        1. COUNT(*) to get total matching cars (before paging)
        2. SELECT with OFFSET/LIMIT to get paginated results

        Args:
            filters: Filter criteria (AND semantics) - must be pre-validated
            paging: Pagination parameters - must be pre-validated

        Returns:
            SearchResult with cars and total_count

        Note:
            Assumes inputs are validated by UseCase (contract programming).
        """
        # Trust that UseCase has validated inputs (contract programming)

        # Build base query with filters
        query = self._build_query(filters)

        # Execute COUNT query for total_count (before paging)
        count_query = select(func.count()).select_from(query.subquery())
        total_count = self._session.execute(count_query).scalar() or 0

        # Apply paging to get results
        query = query.offset(paging.offset).limit(paging.limit)

        # Execute query and convert to domain entities
        rows = self._session.execute(query).scalars().all()
        cars = [self._to_domain(row) for row in rows]

        return SearchResult(cars=cars, total_count=total_count)

    def get_by_id(self, car_id: str) -> Car | None:
        """
        Get car by ID.

        Args:
            car_id: Car ID (expected to be a valid UUID string)

        Returns:
            Car entity if found, None otherwise
        """
        try:
            query = select(CarRow).where(CarRow.id == UUID(car_id))
            row = self._session.execute(query).scalar_one_or_none()
            return self._to_domain(row) if row else None
        except ValueError:  # Invalid UUID format
            return None

    def _build_query(self, filters: CatalogFilters) -> Select[tuple[CarRow]]:
        """
        Build SQLAlchemy query with filters applied.

        Args:
            filters: Filter criteria to apply

        Returns:
            SQLAlchemy select statement with WHERE clauses
        """
        query = select(CarRow)

        # Case-insensitive exact match for make
        if filters.make:
            query = query.where(func.lower(CarRow.make) == func.lower(filters.make))

        # Case-insensitive exact match for model
        if filters.model:
            query = query.where(func.lower(CarRow.model) == func.lower(filters.model))

        # Year range filters (inclusive)
        if filters.year_min is not None:
            query = query.where(CarRow.year >= filters.year_min)
        if filters.year_max is not None:
            query = query.where(CarRow.year <= filters.year_max)

        # Price range filters (inclusive)
        if filters.price_min is not None:
            query = query.where(CarRow.price >= filters.price_min)
        if filters.price_max is not None:
            query = query.where(CarRow.price <= filters.price_max)

        return query

    def _to_domain(self, row: CarRow) -> Car:
        """
        Convert database model (CarRow) to domain entity (Car).

        Args:
            row: SQLAlchemy CarRow model

        Returns:
            Car domain entity
        """
        return Car(
            id=str(row.id),  # Convert UUID to string
            make=row.make,
            model=row.model,
            year=row.year,
            price=row.price,  # Already Decimal from NUMERIC column
            trim=row.trim,
            mileage_km=row.mileage_km,
            transmission=row.transmission,
            fuel_type=row.fuel_type,
            body_type=row.body_type,
            location=row.location,
            url=row.url,
        )
